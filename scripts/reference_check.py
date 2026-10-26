"""Independent Decimal reference for the known, duplicate-free EPA snapshot.

This deliberately does not reimplement Spark's generic malformed/conflict rules.
It validates every published daily result of the separately inspected real input.
"""

import csv
import io
import json
import math
import os
import time
import zipfile
from decimal import Decimal
from pathlib import Path

from pm10.ingest import sha256, write_json
from pm10.store import COLUMNS, connect

start = time.monotonic()
data = Path(os.getenv("PM10_DATA", "runtime"))
manifest = json.loads((data / "source-2024.json").read_text())
expected = "2db9732577123284e7f94b581b135c30feae5c7c2d8623d1def66db722d78da4"
assert sha256(data / manifest["archive"]) == expected, (
    "Reference applies only to the inspected snapshot"
)
policy = json.loads(Path("/app/config/quality.json").read_text())
groups = {}
rows = 0
with zipfile.ZipFile(data / manifest["archive"]) as archive:
    with archive.open("hourly_81102_2024.csv") as member:
        for r in csv.DictReader(io.TextIOWrapper(member, encoding="utf-8-sig", newline="")):
            rows += 1
            key = tuple(
                r[c]
                for c in [
                    "State Code",
                    "County Code",
                    "Site Num",
                    "Parameter Code",
                    "POC",
                    "Date Local",
                ]
            )
            if key not in groups:
                groups[key] = {
                    "n_observed": 0,
                    "n_usable": 0,
                    "n_review": 0,
                    "n_negative": 0,
                    "n_flagged": 0,
                    "n_events": 0,
                    "methods": set(),
                    "sum_all": Decimal(0),
                    "sum_used": Decimal(0),
                    "min_pm10": None,
                    "max_pm10": None,
                }
            g = groups[key]
            v = Decimal(r["Sample Measurement"])
            q = r["Qualifier"]
            decision = policy["qualifiers"].get(q, {"action": "include", "type": ""})
            assert not q or q in policy["qualifiers"]
            g["n_observed"] += 1
            g["sum_all"] += v
            g["methods"].add(r["Method Code"])
            g["n_negative"] += v < 0
            g["n_flagged"] += bool(q)
            g["n_events"] += decision["type"] in ["INFORM", "REQEXC"]
            if decision["action"] == "review":
                g["n_review"] += 1
            else:
                g["n_usable"] += 1
                g["sum_used"] += v
                g["min_pm10"] = v if g["min_pm10"] is None else min(v, g["min_pm10"])
                g["max_pm10"] = v if g["max_pm10"] is None else max(v, g["max_pm10"])
assert rows == 3870976
checked = 0
max_error = 0.0
differences = []
with connect() as conn, conn.transaction(), conn.cursor(name="daily_reference") as cur:
    cur.execute("SELECT " + ",".join(COLUMNS) + " FROM daily_feature WHERE dataset='epa_pm10_2024'")
    for values in cur:
        actual = dict(zip(COLUMNS, values))
        key = tuple(str(actual[c]) for c in COLUMNS[:6])
        g = groups.pop(key)
        expected_row = {
            k: g[k]
            for k in [
                "n_observed",
                "n_usable",
                "n_review",
                "n_negative",
                "n_flagged",
                "n_events",
                "min_pm10",
                "max_pm10",
            ]
        }
        expected_row.update(
            n_methods=len(g["methods"]),
            mean_observed=g["sum_all"] / g["n_observed"],
            mean_pm10=g["sum_used"] / g["n_usable"] if g["n_usable"] else None,
            eligible=g["n_usable"] >= 18 and len(g["methods"]) == 1,
        )
        for col, value in expected_row.items():
            a = actual[col]
            if isinstance(value, Decimal):
                if a is not None:
                    max_error = max(max_error, abs(float(value) - a))
                ok = a is not None and math.isclose(float(value), a, rel_tol=1e-10, abs_tol=1e-9)
            else:
                ok = a == value
            if not ok and len(differences) < 20:
                differences.append({"key": key, "column": col, "expected": str(value), "actual": a})
        checked += 1
report = {
    "input_rows": rows,
    "daily_rows_checked": checked,
    "missing_days": len(groups),
    "differences": differences,
    "max_absolute_float_error": max_error,
    "seconds": round(time.monotonic() - start, 3),
    "method": "Independent streaming Python csv + Decimal aggregation, all daily rows; known duplicate-free snapshot",
    "passed": not differences and not groups and checked == 163381,
}
write_json(data / "reference-check.json", report)
print(json.dumps(report, indent=2))
assert report["passed"]
