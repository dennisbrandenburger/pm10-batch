import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

from .ingest import extract, ingest, sha256, write_json

ROOT = Path(__file__).resolve().parent.parent


def recipe_hash():
    h = hashlib.sha256()
    for filename in ["requirements.txt", "Dockerfile"]:
        h.update((ROOT / filename).read_bytes())
    for folder in ["pm10", "config", "sql"]:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                h.update(str(path.relative_to(ROOT)).encode())
                h.update(path.read_bytes())
    # Runtime versions are part of the computation identity.
    import pyspark

    h.update(f"{sys.version_info[:3]}|{pyspark.__version__}".encode())
    return h.hexdigest()


def run(data, year, force=False, failpoint=None):
    from . import store
    from .transform import spark_session, transform

    data = Path(data)
    manifest = json.loads((data / f"source-{year}.json").read_text())
    if sha256(data / manifest["archive"]) != manifest["sha256"]:
        raise ValueError("Raw archive has been modified")
    recipe = recipe_hash()
    run_id = str(uuid.uuid4())
    output = data / "runs" / run_id
    started = time.monotonic()
    with store.connect() as conn:
        store.acquire_lock(conn, manifest["dataset"])
        if not force and store.unchanged(conn, manifest, recipe):
            result = {
                "status": "skipped",
                "reason": "Source, recipe and stored result unchanged",
                "dataset": manifest["dataset"],
            }
            write_json(data / "last-result.json", result)
            return result
        store.start_run(conn, run_id, manifest, recipe)
        spark = None
        committed = False
        try:
            csv = extract(data, manifest, output / "work")
            policy = json.loads((ROOT / "config/quality.json").read_text())
            spark = spark_session()
            spark.sparkContext.setLogLevel("WARN")
            metrics = transform(spark, csv, year, policy, output)
            spark.stop()
            spark = None
            metrics["processing_seconds"] = round(time.monotonic() - started, 3)
            result = store.publish(conn, output, run_id, manifest, recipe, metrics, failpoint)
            committed = True
            report = {
                "status": "succeeded",
                "run_id": run_id,
                "source": manifest,
                "recipe_sha256": recipe,
                "metrics": metrics,
                **result,
                "total_seconds": round(time.monotonic() - started, 3),
            }
            write_json(output / "report.json", report)
            write_json(data / "last-result.json", report)
            return report
        except Exception as exc:
            if not committed:
                store.fail_run(conn, run_id, exc)
            write_json(
                output / "failure.json",
                {
                    "status": "failed",
                    "run_id": run_id,
                    "error": str(exc),
                    "seconds": round(time.monotonic() - started, 3),
                },
            )
            raise
        finally:
            if spark:
                spark.stop()
            shutil.rmtree(output / "work", ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="EPA PM10 batch pipeline")
    parser.add_argument("command", choices=["ingest", "run", "status"])
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--failpoint", choices=["after_delete"])
    args = parser.parse_args()
    data = Path(os.getenv("PM10_DATA", "runtime"))
    if args.command == "ingest":
        result = ingest(data, args.year, args.archive, args.expected_sha256)
    elif args.command == "run":
        result = run(data, args.year, args.force, args.failpoint)
    else:
        from .store import connect

        with connect() as conn:
            result = {
                "datasets": [
                    dict(
                        zip(
                            [
                                "dataset",
                                "run_id",
                                "source_sha256",
                                "recipe_sha256",
                                "result_sha256",
                                "row_count",
                            ],
                            r,
                        )
                    )
                    for r in conn.execute("SELECT * FROM active_dataset").fetchall()
                ]
            }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
