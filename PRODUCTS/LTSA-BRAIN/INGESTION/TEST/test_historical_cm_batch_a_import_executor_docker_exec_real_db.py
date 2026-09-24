"""LTSA_HISTORICAL_CM_BATCH_A_R2_DOCKER_EXEC_READ_FIX_R1 -- the executor over
DatabaseRunner's docker-compose transport (`docker compose exec -T postgres
psql -tAc ...`), the transport the production host uses.

psql -tAc prints the command tag of every statement in a multi-statement
string, so the executor's read-only reads ("BEGIN TRANSACTION READ ONLY;
SELECT ...") come back as "BEGIN\\n<result>". These tests run against a disposable compose project
(postgres:16-alpine, service "postgres"), created and removed here; they are
skipped when docker is unavailable. The direct-connect transport is covered by
test_historical_cm_batch_a_import_executor_real_db.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

_INGESTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_INGESTION_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import historical_cm_batch_a_import_executor as executor  # noqa: E402
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner  # noqa: E402
from test_historical_cm_batch_a_import_executor import _ASSETS, _manifest_document, _parse  # noqa: E402
from test_historical_cm_batch_a_import_executor_real_db import (  # noqa: E402
    _DATABASE_DIR,
    _MIGRATION_038,
    _MIGRATIONS,
    _docker_available,
)

_PROJECT = "ai5r-test-hist-cm-docker-exec"
_COMPOSE = """services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
"""

pytestmark = pytest.mark.skipif(not _docker_available(), reason="docker daemon unavailable")


def _compose(env_file: Path, compose_file: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-p", _PROJECT, "--env-file", str(env_file), "-f", str(compose_file), *args],
        capture_output=True, text=True,
    )


@pytest.fixture(scope="module")
def runner(tmp_path_factory):
    directory = tmp_path_factory.mktemp("compose")
    env_file = directory / ".env"
    env_file.write_text(
        f"COMPOSE_PROJECT_NAME={_PROJECT}\nPOSTGRES_USER=ai5r\nPOSTGRES_PASSWORD=disposable\nPOSTGRES_DB=ltsa_brain\n",
        encoding="utf-8",
    )
    compose_file = directory / "compose.yaml"
    compose_file.write_text(_COMPOSE, encoding="utf-8")
    _compose(env_file, compose_file, "down", "-v")
    started = _compose(env_file, compose_file, "up", "-d")
    assert started.returncode == 0, started.stderr
    try:
        r = DatabaseRunner(
            DatabaseConfig(env_file=env_file, compose_file=compose_file, service="postgres", user="ai5r", database="ltsa_brain")
        )
        for _ in range(60):
            ready = _compose(env_file, compose_file, "exec", "-T", "postgres", "pg_isready", "-U", "ai5r", "-d", "ltsa_brain")
            if ready.returncode == 0:
                break
            time.sleep(1)
        time.sleep(2)
        for script in [_DATABASE_DIR / "CANONICAL_SCHEMA.sql", *_MIGRATIONS]:
            r.execute_script(script.read_text(encoding="utf-8"))
        r.execute_script(_MIGRATION_038)
        values = ", ".join(f"('{asset}', 'Pump {asset}', 'PUMP', 'HCC')" for asset in _ASSETS)
        pumps = ", ".join(f"('{asset}', 'HCC', 'MASTER-PLAN-53B')" for asset in _ASSETS)
        r.execute_script(
            f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area) VALUES {values};\n"
            f"INSERT INTO ltsa_pumps (tag_number, area, api_plan) VALUES {pumps};\n"
            "INSERT INTO condition_monitoring_reading "
            "(condition_monitoring_reading_code, condition_monitoring_schedule_code, asset_code, asset_type, reading_date) "
            "SELECT 'CMONR-EXIST' || lpad(n::text, 6, '0'), 'UNSCHEDULED::SEED', 'SEED-P-' || (n % 50), 'PUMP', "
            "DATE '2024-01-01' + n FROM generate_series(0, 2091) AS n;"
        )
        yield r
    finally:
        _compose(env_file, compose_file, "down", "-v")


@pytest.fixture(scope="module")
def manifest():
    return _parse(_manifest_document())


def test_transport_prints_the_transaction_status_before_the_result(runner):
    raw = runner.query_scalar("BEGIN TRANSACTION READ ONLY; SELECT count(*) FROM condition_monitoring_reading;")
    assert raw.splitlines() == ["BEGIN", "2092"]


def test_scalar_read_returns_only_the_result(runner):
    store = executor.PostgresCmImportStore(runner)
    assert store.count_total() == 2092
    assert store.has_column("condition_monitoring_reading", "api_plan_snapshot") is True
    assert store.count_with_reference_prefix(executor.SOURCE_REFERENCE_PREFIX) == 0


def test_json_read_returns_the_complete_multi_line_result(runner):
    raw = runner.query_scalar(
        "BEGIN TRANSACTION READ ONLY; SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') "
        "FROM (SELECT asset_code, asset_type FROM asset_registry ORDER BY asset_code LIMIT 3) t;"
    )
    assert raw.splitlines()[0] == "BEGIN"
    assert [a["asset_code"] for a in json.loads(executor._query_result(raw))] == sorted(_ASSETS)[:3]
    store = executor.PostgresCmImportStore(runner)
    assets = store.registry_assets(_ASSETS[:5])
    assert sorted(a["asset_code"] for a in assets) == sorted(_ASSETS[:5])
    assert all(a["asset_type"] == "PUMP" for a in assets)


def test_read_is_read_only_on_this_transport(runner):
    store = executor.PostgresCmImportStore(runner)
    with pytest.raises(subprocess.CalledProcessError):
        store._read("INSERT INTO asset_registry (asset_code, asset_name) VALUES ('RO-TEST', 'x') RETURNING 1;")
    assert store.count_total() == 2092


def test_full_dry_run_apply_and_idempotency_over_docker_exec(runner, manifest):
    store = executor.PostgresCmImportStore(runner)
    plan = executor.preflight(manifest, store)
    assert len(plan.proposed) == 2907 and plan.total_now == 2092
    result = executor.apply(manifest, store, plan, batch_size=500)
    assert result["inserted"] == 2907
    assert result["verification"]["TOTAL_AFTER"] == 4999
    assert result["verification"]["MANIFEST_ROWS_IDENTICAL"] is True
    assert result["verification"]["PREEXISTING_ROWS_UNCHANGED"] is True
    assert result["verification"]["SECOND_DRY_RUN_PROPOSED_INSERTS"] == 0
    stored = {
        row["source_reference"]: row
        for row in store.rows_by_reference_or_code(
            [r.source_reference for r in manifest.rows], [r.reading_code for r in manifest.rows]
        )
    }
    for row in manifest.rows:
        for name in executor.LEAK_FIELDS:
            assert stored[row.source_reference][name] is row.measurements[name]
        assert stored[row.source_reference]["api_plan_snapshot"] == row.api_plan_snapshot
