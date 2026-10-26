import csv
import os
import uuid
from pathlib import Path

import pytest
from psycopg import sql

from pm10 import store


@pytest.fixture
def database():
    assert os.environ["PGDATABASE"].endswith("_test"), "Use a separate test database"
    schema = "test_" + uuid.uuid4().hex
    with store.connect() as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        conn.execute(Path("/app/sql/schema.sql").read_text())
        yield conn
        conn.execute("SET search_path TO public")
        conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def publish(conn, tmp_path, manifest, recipe="recipe-a", value=10, failpoint=None):
    run_id = str(uuid.uuid4())
    folder = tmp_path / run_id / "daily"
    folder.mkdir(parents=True)
    row = [
        "01",
        "001",
        "0001",
        "81102",
        "1",
        "2024-01-01",
        24,
        24,
        0,
        0,
        0,
        0,
        1,
        value,
        value,
        value,
        value,
        True,
    ]
    with (folder / "part-000.csv").open("w", newline="") as f:
        csv.writer(f).writerow(row)
    store.start_run(conn, run_id, manifest, recipe)
    try:
        return store.publish(
            conn, folder.parent, run_id, manifest, recipe, {"daily_rows": 1}, failpoint
        )
    except Exception as exc:
        store.fail_run(conn, run_id, exc)
        raise


def test_atomic_rollback_idempotency_and_output_repair(database, tmp_path):
    conn = database
    m = {"dataset": "test", "sha256": "a" * 64}
    store.acquire_lock(conn, m["dataset"])
    original = publish(conn, tmp_path, m)
    assert store.unchanged(conn, m, "recipe-a")
    assert not store.unchanged(conn, m, "changed-rule")
    assert not store.unchanged(conn, {**m, "sha256": "b" * 64}, "recipe-a")
    with pytest.raises(RuntimeError, match="after DELETE"):
        publish(conn, tmp_path, m, value=20, failpoint="after_delete")
    assert store.result_digest(conn, "test") == (original["result_sha256"], 1)
    assert (
        conn.execute("SELECT count(*) FROM pipeline_run WHERE status='failed'").fetchone()[0] == 1
    )
    conn.execute("UPDATE daily_feature SET mean_pm10=11,max_pm10=11")
    assert not store.unchanged(conn, m, "recipe-a")
    publish(conn, tmp_path, m)
    assert store.unchanged(conn, m, "recipe-a")
    conn.execute("DELETE FROM daily_feature")
    assert not store.unchanged(conn, m, "recipe-a")
    publish(conn, tmp_path, m)
    assert store.unchanged(conn, m, "recipe-a")
    with store.connect() as other, pytest.raises(RuntimeError, match="lock"):
        store.acquire_lock(other, "test")
    assert (
        conn.execute("SELECT rolsuper FROM pg_roles WHERE rolname=current_user").fetchone()[0]
        is False
    )
