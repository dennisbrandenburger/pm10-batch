"""Explicit schema validation and aggregation by AQS monitor and local day."""

from pathlib import Path

from pyspark import StorageLevel
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

from .ingest import HEADERS

KEY = ["state", "county", "site", "parameter", "poc"]
DAILY_COLUMNS = KEY + [
    "day",
    "n_observed",
    "n_usable",
    "n_review",
    "n_negative",
    "n_flagged",
    "n_events",
    "n_methods",
    "mean_observed",
    "mean_pm10",
    "min_pm10",
    "max_pm10",
    "eligible",
]


def spark_session():
    return (
        SparkSession.builder.master("local[4]")
        .appName("epa-pm10-batch")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "24")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )


def transform(spark, path, year, policy, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    schema = T.StructType([T.StructField(c, T.StringType()) for c in HEADERS])
    raw = (
        spark.read.option("header", True)
        .option("mode", "FAILFAST")
        .option("enforceSchema", False)
        .schema(schema)
        .csv(str(path))
    )
    # All source fields participate in exact duplicate detection, including metadata.
    total = raw.count()
    unique = raw.dropDuplicates(HEADERS)
    df = unique.select(
        F.col("State Code").alias("state"),
        F.col("County Code").alias("county"),
        F.col("Site Num").alias("site"),
        F.col("Parameter Code").alias("parameter"),
        F.col("POC").alias("poc"),
        F.col("Date Local").alias("local_date"),
        F.col("Time Local").alias("local_time"),
        F.col("Date GMT").alias("gmt_date"),
        F.col("Time GMT").alias("gmt_time"),
        F.col("Sample Measurement").alias("measurement"),
        F.col("Units of Measure").alias("unit"),
        F.col("Latitude").alias("latitude"),
        F.col("Longitude").alias("longitude"),
        F.coalesce(F.col("Qualifier"), F.lit("")).alias("qualifier"),
        F.col("Method Code").alias("method"),
        F.col("Datum").alias("datum"),
    )
    df = (
        df.withColumn("value", F.expr("try_cast(measurement as double)"))
        .withColumn("lat", F.expr("try_cast(latitude as double)"))
        .withColumn("lon", F.expr("try_cast(longitude as double)"))
        .withColumn(
            "local_ts",
            F.try_to_timestamp(
                F.concat_ws(" ", "local_date", "local_time"), F.lit("yyyy-MM-dd HH:mm")
            ),
        )
        .withColumn(
            "gmt_ts",
            F.try_to_timestamp(F.concat_ws(" ", "gmt_date", "gmt_time"), F.lit("yyyy-MM-dd HH:mm")),
        )
    )
    valid = (
        F.col("state").rlike(r"^\d{2}$")
        & F.col("county").rlike(r"^\d{3}$")
        & F.col("site").rlike(r"^\d{4}$")
        & F.col("poc").rlike(r"^[1-9]\d?$")
        & (F.col("parameter") == policy["parameter"])
        & (F.col("unit") == policy["unit"])
        & F.col("value").isNotNull()
        & ~F.isnan("value")
        & (F.abs(F.col("value")) < float("inf"))
        & F.col("lat").between(-90, 90)
        & F.col("lon").between(-180, 180)
        & F.col("local_ts").isNotNull()
        & F.col("gmt_ts").isNotNull()
        & (F.year("local_ts") == year)
        & F.col("local_time").rlike(r"^\d{2}:00$")
        & F.col("gmt_time").rlike(r"^\d{2}:00$")
        & (
            (F.col("gmt_ts").cast("long") - F.col("local_ts").cast("long")).between(
                -14 * 3600, 14 * 3600
            )
        )
        & F.col("method").rlike(r"^\d{3}$")
    )
    df = df.withColumn("structural_ok", F.coalesce(valid, F.lit(False))).persist(
        StorageLevel.MEMORY_AND_DISK
    )
    unique_count = df.count()
    unknown = [
        r[0]
        for r in df.select("qualifier").distinct().collect()
        if r[0] and r[0] not in policy["qualifiers"]
    ]
    if unknown:
        df.unpersist()
        raise ValueError(f"Unreviewed qualifier codes: {sorted(unknown)}")
    invalid_count = df.filter(~F.col("structural_ok")).count()
    df.filter(~F.col("structural_ok")).write.mode("overwrite").parquet(str(output / "invalid"))
    good = df.filter("structural_ok")
    # Preserve every conflicting observation for review; never choose an arbitrary winner.
    good = good.withColumn(
        "local_count", F.count("*").over(Window.partitionBy(*(KEY + ["local_ts"])))
    ).withColumn("gmt_count", F.count("*").over(Window.partitionBy(*(KEY + ["gmt_ts"]))))
    review_codes = [k for k, v in policy["qualifiers"].items() if v["action"] == "review"]
    event_codes = [k for k, v in policy["qualifiers"].items() if v["type"] in ["INFORM", "REQEXC"]]
    good = (
        good.withColumn("conflict", (F.col("local_count") > 1) | (F.col("gmt_count") > 1))
        .withColumn("review", F.col("qualifier").isin(review_codes))
        .withColumn("usable", ~F.col("conflict") & ~F.col("review"))
        .withColumn("event", F.col("qualifier").isin(event_codes))
        .withColumn("day", F.to_date("local_ts"))
        .persist(StorageLevel.MEMORY_AND_DISK)
    )
    counts = (
        good.agg(
            F.count("*").alias("structural_rows"),
            F.sum(F.col("conflict").cast("long")).alias("conflicting_rows"),
            F.sum(F.col("usable").cast("long")).alias("usable_rows"),
            F.sum((F.col("value") < 0).cast("long")).alias("negative_rows"),
            F.sum((F.col("qualifier") != "").cast("long")).alias("flagged_rows"),
        )
        .first()
        .asDict()
    )
    good.filter(~F.col("usable")).write.mode("overwrite").parquet(str(output / "review"))
    # Count observed hours independently of conflicting extra records.
    daily = good.groupBy(*(KEY + ["day"])).agg(
        F.countDistinct("local_ts").alias("n_observed"),
        F.sum(F.col("usable").cast("long")).alias("n_usable"),
        F.sum((~F.col("usable")).cast("long")).alias("n_review"),
        F.sum((F.col("value") < 0).cast("long")).alias("n_negative"),
        F.sum((F.col("qualifier") != "").cast("long")).alias("n_flagged"),
        F.sum(F.col("event").cast("long")).alias("n_events"),
        F.countDistinct("method").alias("n_methods"),
        F.avg(F.when(~F.col("conflict"), F.col("value"))).alias("mean_observed"),
        F.avg(F.when(F.col("usable"), F.col("value"))).alias("mean_pm10"),
        F.min(F.when(F.col("usable"), F.col("value"))).alias("min_pm10"),
        F.max(F.when(F.col("usable"), F.col("value"))).alias("max_pm10"),
    )
    daily = (
        daily.withColumn(
            "eligible",
            (F.col("n_usable") >= policy["minimum_hours"]) & (F.col("n_methods") == 1),
        )
        .select(DAILY_COLUMNS)
        .persist(StorageLevel.MEMORY_AND_DISK)
    )
    summary = (
        daily.agg(
            F.count("*").alias("daily_rows"),
            F.sum(F.col("eligible").cast("long")).alias("eligible_days"),
            F.sum((F.col("n_usable") == 24).cast("long")).alias("complete_days"),
        )
        .first()
        .asDict()
    )
    if not summary["daily_rows"]:
        raise ValueError("No valid monitor-days: publication refused")
    daily.write.mode("overwrite").option("header", False).option("nullValue", "").csv(
        str(output / "daily")
    )
    metrics = {
        "input_rows": total,
        "exact_duplicates_removed": total - unique_count,
        "invalid_rows": invalid_count,
        **counts,
        **summary,
        "monitor_count": good.select(KEY).distinct().count(),
    }
    daily.unpersist()
    good.unpersist()
    df.unpersist()
    return metrics
