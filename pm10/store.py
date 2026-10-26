"""One atomic replacement per dataset; old results survive failed publications."""

import hashlib
import os
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

COLUMNS = [
    "state",
    "county",
    "site",
    "parameter",
    "poc",
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


def connect():
    return psycopg.connect(
        host=os.getenv("PGHOST", "database"),
        dbname=os.getenv("PGDATABASE", "pm10"),
        user=os.getenv("PGUSER", "pm10"),
        password=Path(os.environ["PM10_PASSWORD_FILE"]).read_text().strip(),
        connect_timeout=15,
        autocommit=True,
    )


def result_digest(conn, dataset):
    columns = sql.SQL(",").join(map(sql.Identifier, COLUMNS))
    query = sql.SQL(
        "COPY (SELECT {} FROM daily_feature WHERE dataset={} ORDER BY state,county,site,parameter,poc,day) TO STDOUT WITH (FORMAT CSV)"
    ).format(columns, sql.Literal(dataset))
    digest = hashlib.sha256()
    with conn.cursor().copy(query) as copy:
        for block in copy:
            digest.update(block)
    count = conn.execute(
        "SELECT count(*) FROM daily_feature WHERE dataset=%s", (dataset,)
    ).fetchone()[0]
    return digest.hexdigest(), count


def acquire_lock(conn, dataset):
    locked = conn.execute(
        "SELECT pg_try_advisory_lock(hashtextextended(%s,0))", (dataset,)
    ).fetchone()[0]
    if not locked:
        raise RuntimeError("Another process holds the dataset lock")


def unchanged(conn, manifest, recipe):
    row = conn.execute(
        "SELECT source_sha256,recipe_sha256,result_sha256,row_count FROM active_dataset WHERE dataset=%s",
        (manifest["dataset"],),
    ).fetchone()
    return bool(
        row
        and row[:2] == (manifest["sha256"], recipe)
        and result_digest(conn, manifest["dataset"]) == row[2:]
    )


def start_run(conn, run_id, manifest, recipe):
    # A crashed predecessor cannot still hold the lock acquired by this process.
    conn.execute(
        "UPDATE pipeline_run SET status='failed', finished_at=now(), error='Interrupted before completion' WHERE dataset=%s AND status='running'",
        (manifest["dataset"],),
    )
    conn.execute(
        "INSERT INTO pipeline_run(run_id,dataset,status,source_sha256,recipe_sha256) VALUES (%s,%s,'running',%s,%s)",
        (run_id, manifest["dataset"], manifest["sha256"], recipe),
    )


def publish(conn, output, run_id, manifest, recipe, metrics, failpoint=None):
    with conn.transaction():
        conn.execute(
            "CREATE TEMP TABLE stage (LIKE daily_feature INCLUDING CONSTRAINTS) ON COMMIT DROP"
        )
        conn.execute("ALTER TABLE stage DROP COLUMN dataset, DROP COLUMN run_id")
        columns = sql.SQL(",").join(map(sql.Identifier, COLUMNS))
        with conn.cursor().copy(
            sql.SQL("COPY stage ({}) FROM STDIN WITH (FORMAT CSV)").format(columns)
        ) as copy:
            for part in sorted((Path(output) / "daily").glob("part-*.csv")):
                with part.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024**2), b""):
                        copy.write(block)
        count = conn.execute("SELECT count(*) FROM stage").fetchone()[0]
        if count != metrics["daily_rows"] or not count:
            raise ValueError("Staging row count does not match Spark report")
        conn.execute("DELETE FROM daily_feature WHERE dataset=%s", (manifest["dataset"],))
        if failpoint == "after_delete":
            raise RuntimeError("Requested failure after DELETE, before INSERT")
        conn.execute(
            sql.SQL(
                "INSERT INTO daily_feature (dataset,{},run_id) SELECT %s,{},%s FROM stage"
            ).format(columns, columns),
            (manifest["dataset"], run_id),
        )
        digest, count = result_digest(conn, manifest["dataset"])
        conn.execute(
            "INSERT INTO active_dataset VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (dataset) DO UPDATE SET run_id=excluded.run_id,source_sha256=excluded.source_sha256,recipe_sha256=excluded.recipe_sha256,result_sha256=excluded.result_sha256,row_count=excluded.row_count",
            (manifest["dataset"], run_id, manifest["sha256"], recipe, digest, count),
        )
        conn.execute(
            "UPDATE pipeline_run SET status='succeeded',finished_at=now(),metrics=%s WHERE run_id=%s",
            (Jsonb(metrics), run_id),
        )
    return {"result_sha256": digest, "row_count": count}


def fail_run(conn, run_id, exc):
    conn.execute(
        "UPDATE pipeline_run SET status='failed',finished_at=now(),error=%s WHERE run_id=%s",
        (str(exc)[:2000], run_id),
    )
