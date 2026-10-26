import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from conftest import write_csv

from pm10.transform import DAILY_COLUMNS, spark_session, transform


@pytest.fixture(scope="module")
def spark():
    s = spark_session()
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


def test_quality_time_conflicts_and_daily_means(tmp_path, row, spark):
    rows = []
    for site, hours in [("0001", 24), ("0002", 18), ("0003", 17)]:
        for h in range(hours):
            r = {
                **row,
                "Site Num": site,
                "Time Local": f"{h:02}:00",
                "Sample Measurement": str(h),
            }
            g = datetime(2024, 1, 1, h) + timedelta(hours=6)
            r.update({"Date GMT": g.strftime("%Y-%m-%d"), "Time GMT": g.strftime("%H:%M")})
            rows.append(r)
    rows.extend(
        [
            {**row, "Site Num": "0004", "Sample Measurement": "-2", "Qualifier": "MD"},
            {
                **row,
                "Site Num": "0005",
                "Sample Measurement": "9257",
                "Qualifier": "IT",
            },
            {**row, "Site Num": "0006", "Qualifier": "QX"},
            {
                **row,
                "Site Num": "0007",
                "Date Local": "2024-12-31",
                "Time Local": "23:00",
                "Date GMT": "2025-01-01",
                "Time GMT": "05:00",
            },
            {**row, "Site Num": "0008", "Sample Measurement": "20"},
            {**row, "Site Num": "0008", "Sample Measurement": "30"},
            {**row, "Site Num": "0009", "Sample Measurement": "NaN"},
            {**row, "Site Num": "0010", "Date Local": "not-a-date"},
        ]
    )
    rows.append(dict(rows[0]))
    path = tmp_path / "input.csv"
    write_csv(path, rows)
    policy = json.loads(Path("/app/config/quality.json").read_text())
    metrics = transform(spark, path, 2024, policy, tmp_path / "out")
    result = {}
    for p in (tmp_path / "out/daily").glob("part-*.csv"):
        for r in csv.DictReader(p.open(), fieldnames=DAILY_COLUMNS):
            result[r["site"]] = r
    assert metrics["input_rows"] == 68
    assert metrics["exact_duplicates_removed"] == 1
    assert metrics["invalid_rows"] == 2
    assert metrics["conflicting_rows"] == 2
    assert metrics["daily_rows"] == 8
    assert metrics["eligible_days"] == 2
    assert float(result["0001"]["mean_pm10"]) == 11.5
    assert float(result["0002"]["mean_pm10"]) == 8.5
    assert result["0003"]["eligible"] == "false"
    assert float(result["0004"]["mean_pm10"]) == -2
    assert result["0004"]["n_negative"] == "1"
    assert float(result["0005"]["mean_pm10"]) == 9257
    assert result["0005"]["n_events"] == "1"
    assert result["0006"]["mean_pm10"] == ""
    assert result["0007"]["day"] == "2024-12-31"
    assert result["0008"]["n_usable"] == "0"


def test_unknown_qualifier_blocks_publication(tmp_path, row, spark):
    path = tmp_path / "input.csv"
    write_csv(path, [{**row, "Qualifier": "NEW_UNKNOWN"}])
    policy = json.loads(Path("/app/config/quality.json").read_text())
    with pytest.raises(ValueError, match="Unreviewed qualifier"):
        transform(spark, path, 2024, policy, tmp_path / "out")


def test_mixed_methods_and_invalid_time_and_unit(tmp_path, row, spark):
    rows = []
    for h in range(24):
        g = datetime(2024, 1, 1, h) + timedelta(hours=6)
        rows.append(
            {
                **row,
                "Time Local": f"{h:02}:00",
                "Date GMT": g.strftime("%Y-%m-%d"),
                "Time GMT": g.strftime("%H:%M"),
                "Method Code": "239" if h < 12 else "245",
            }
        )
    rows.extend(
        [
            {**row, "Site Num": "0002", "Units of Measure": "ppb"},
            {**row, "Site Num": "0003", "Time Local": "00:30"},
            {**row, "Site Num": "0004", "Date GMT": "2024-02-01"},
        ]
    )
    path = tmp_path / "input.csv"
    write_csv(path, rows)
    policy = json.loads(Path("/app/config/quality.json").read_text())
    result = transform(spark, path, 2024, policy, tmp_path / "out")
    assert result["invalid_rows"] == 3
    assert result["daily_rows"] == 1
    assert result["eligible_days"] == 0
    assert result["usable_rows"] == 24
