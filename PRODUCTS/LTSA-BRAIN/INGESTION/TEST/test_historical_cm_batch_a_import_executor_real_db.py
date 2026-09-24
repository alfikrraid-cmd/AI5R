"""LTSA_HISTORICAL_CM_BATCH_A_IMPORT_EXECUTOR_R1 -- the executor's real SQL
against a REAL, disposable Postgres (local docker container, created and
removed by this module; never a shared or production database).

What only a real database can prove: the batch script's DO-block prechecks,
the multi-row INSERT and the postcheck really are one transaction -- when a
row in the middle of a batch is rejected by Postgres, none of that batch's
rows survive and earlier committed batches are untouched; reads really are
read-only; and api_plan_snapshot stays NULL even though ltsa_pumps carries a
master API Plan for the same pump.

Same pg_port / DatabaseRunner / bootstrap_schema fixture shape as
CORE-SERVICES/API/TESTS/test_condition_monitoring_reading_bulk_atomicity_real_db.py.
Skipped when docker is unavailable.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

_INGESTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_INGESTION_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import historical_cm_batch_a_import_executor as executor  # noqa: E402
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from test_historical_cm_batch_a_import_executor import _ASSETS, _manifest_document, _parse  # noqa: E402

_CONTAINER_NAME = "ai5r-test-hist-cm-batch-a-executor-pg"
_USER = "ai5r"
_PASSWORD = "test-hist-cm-batch-a-password"
_DATABASE = "ltsa_brain"
_DATABASE_DIR = _INGESTION_DIR.parent / "DATABASE"
_MIGRATIONS = [
    _DATABASE_DIR / "MIGRATIONS" / name
    for name in (
        "007_create_ltsa_auth_foundation.sql",
        "008_create_internal_component_inventory.sql",
        "009_create_installation_report.sql",
        "010_alter_document_field_extraction_review_provenance.sql",
        "011_alter_installation_report_post_installation_readings.sql",
        "012_alter_auth_foundation_attribution.sql",
        "013_alter_seal_registry_identifiers_attribution.sql",
        "014_alter_pm_cmon_workflow_and_evidence.sql",
        "015_alter_historical_pm_cmon_ingestion.sql",
        "016_alter_organization_membership_data_scope.sql",
        "017_create_record_change_history.sql",
        "023_create_pm_cmon_base_tables_for_legacy_upgrade.sql",
        "027_add_pm_cmon_soft_delete.sql",
        "028_add_schedule_attribution_soft_delete.sql",
        "029_add_condition_monitoring_schedule_lifecycle.sql",
    )
]
# Migration 038 (dashboard branch, applied in production): the one statement.
_MIGRATION_038 = "ALTER TABLE public.condition_monitoring_reading ADD COLUMN IF NOT EXISTS api_plan_snapshot TEXT;"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, text=True).returncode == 0


pytestmark = pytest.mark.skipif(not _docker_available(), reason="docker daemon unavailable")


@pytest.fixture(scope="module")
def runner():
    subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _CONTAINER_NAME,
            "-e", f"POSTGRES_USER={_USER}", "-e", f"POSTGRES_PASSWORD={_PASSWORD}", "-e", f"POSTGRES_DB={_DATABASE}",
            "-p", "127.0.0.1::5432", "postgres:16-alpine",
        ],
        check=True, capture_output=True, text=True,
    )
    try:
        port = int(
            subprocess.run(["docker", "port", _CONTAINER_NAME, "5432/tcp"], check=True, capture_output=True, text=True)
            .stdout.strip().splitlines()[0].rsplit(":", 1)[1]
        )
        r = DatabaseRunner(DatabaseConfig(host="127.0.0.1", port=port, user=_USER, password=_PASSWORD, database=_DATABASE))
        last_error: Exception | None = None
        for _ in range(60):
            try:
                r.query_scalar("SELECT 1")
                last_error = None
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(1)
        if last_error is not None:
            raise RuntimeError(f"Test Postgres never became ready: {last_error}")
        bootstrap_schema(r, _DATABASE_DIR / "CANONICAL_SCHEMA.sql")
        for migration in _MIGRATIONS:
            bootstrap_schema(r, migration)
        r.execute_script(_MIGRATION_038)
        yield r
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def seeded(runner):
    """2,092 pre-existing readings + 202 PUMP assets (+ master API Plans)."""
    runner.execute_script(
        "TRUNCATE condition_monitoring_reading, asset_registry, ltsa_pumps RESTART IDENTITY CASCADE;\n"
        "ALTER TABLE condition_monitoring_reading DROP CONSTRAINT IF EXISTS test_reject_one_row;"
    )
    values = ", ".join(f"('{asset}', 'Pump {asset}', 'PUMP', 'HCC')" for asset in _ASSETS)
    pumps = ", ".join(f"('{asset}', 'HCC', 'MASTER-PLAN-53B')" for asset in _ASSETS)
    assets_array = "ARRAY[" + ", ".join(f"'{asset}'" for asset in _ASSETS) + "]"
    runner.execute_script(
        f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area) VALUES {values};\n"
        f"INSERT INTO ltsa_pumps (tag_number, area, api_plan) VALUES {pumps};\n"
        "INSERT INTO condition_monitoring_reading "
        "(condition_monitoring_reading_code, condition_monitoring_schedule_code, asset_code, asset_type, reading_date, "
        " mechanical_seal_leak_de, provenance, source_reference) "
        "SELECT 'CMONR-EXIST' || lpad(n::text, 6, '0'), 'UNSCHEDULED::SEED', "
        f"({assets_array})[1 + n % {len(_ASSETS)}], 'PUMP', DATE '2024-01-01' + (n / {len(_ASSETS)}), "
        "n % 2 = 0, 'MANUAL', CASE WHEN n % 2 = 0 THEN 'document_field_extraction:DFE-' || n END "
        "FROM generate_series(0, 2091) AS n;"
    )
    return runner


@pytest.fixture(scope="module")
def manifest():
    return _parse(_manifest_document())


def _table_md5(runner: DatabaseRunner, table: str, order: str) -> str:
    return runner.query_scalar(f"SELECT md5(string_agg(t::text, ',' ORDER BY {order})) FROM {table} t;")


def test_reads_run_in_a_read_only_transaction(seeded):
    store = executor.PostgresCmImportStore(seeded)
    with pytest.raises(Exception) as excinfo:
        store._read("INSERT INTO asset_registry (asset_code, asset_name) VALUES ('RO-TEST', 'x') RETURNING 1;")
    assert "read-only" in str(excinfo.value)
    assert seeded.query_scalar("SELECT count(*) FROM asset_registry WHERE asset_code = 'RO-TEST';") == "0"


def test_dry_run_proposes_2907_on_real_schema(seeded, manifest):
    plan = executor.preflight(manifest, executor.PostgresCmImportStore(seeded))
    assert len(plan.proposed) == 2907 and plan.total_now == 2092
    assert seeded.query_scalar("SELECT count(*) FROM condition_monitoring_reading;") == "2092"


def test_baseline_change_aborts_on_real_schema(seeded, manifest):
    seeded.execute_script(
        "INSERT INTO condition_monitoring_reading (condition_monitoring_reading_code, condition_monitoring_schedule_code, "
        "asset_code, reading_date) VALUES ('CMONR-EXTRA', 'UNSCHEDULED::SEED', 'OTHER-P-1', '2024-06-01');"
    )
    with pytest.raises(executor.ExecutorAbort) as excinfo:
        executor.preflight(manifest, executor.PostgresCmImportStore(seeded))
    assert "BASELINE_CHANGED" in {issue["code"] for issue in excinfo.value.details["issues"]}


def test_sql_precheck_rolls_back_whole_batch_on_stale_baseline(seeded, manifest):
    store = executor.PostgresCmImportStore(seeded)
    with pytest.raises(Exception) as excinfo:
        store.insert_batch(list(manifest.rows[:250]), expected_total_before=2091)
    assert "BASELINE_CHANGED" in str(excinfo.value)
    assert seeded.query_scalar("SELECT count(*) FROM condition_monitoring_reading;") == "2092"


def test_failed_batch_rolls_back_then_resume_completes_idempotently(seeded, manifest):
    store = executor.PostgresCmImportStore(seeded)
    assets_before = _table_md5(seeded, "asset_registry", "asset_code")
    pumps_before = _table_md5(seeded, "ltsa_pumps", "tag_number")
    plan = executor.preflight(manifest, store)

    # A Postgres-level rejection of ONE row in the middle of batch 2: the
    # INSERT statement itself fails after the precheck already passed.
    victim = plan.proposed[260].source_reference
    seeded.execute_script(
        "ALTER TABLE condition_monitoring_reading ADD CONSTRAINT test_reject_one_row "
        f"CHECK (source_reference IS DISTINCT FROM '{victim}');"
    )
    with pytest.raises(executor.BatchFailed) as excinfo:
        executor.apply(manifest, store, plan, batch_size=250)
    details = excinfo.value.details
    assert details["failed_batch"] == 2 and details["committed_batches"] == 1
    assert details["rolled_back_cleanly"] is True
    assert seeded.query_scalar("SELECT count(*) FROM condition_monitoring_reading;") == str(2092 + 250)
    batch_two = ", ".join(f"'{row.source_reference}'" for row in plan.proposed[250:500])
    assert seeded.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading WHERE source_reference IN ({batch_two});"
    ) == "0"

    # Resume is refused unless explicitly requested.
    seeded.execute_script("ALTER TABLE condition_monitoring_reading DROP CONSTRAINT test_reject_one_row;")
    with pytest.raises(executor.ExecutorAbort):
        executor.preflight(manifest, store)
    resumed = executor.preflight(manifest, store, allow_resume=True)
    assert len(resumed.proposed) == 2907 - 250

    result = executor.apply(manifest, store, resumed, batch_size=250)
    verification = result["verification"]
    assert verification["TOTAL_AFTER"] == 4999
    assert verification["PREEXISTING_ROWS_UNCHANGED"] is True
    assert verification["MANIFEST_ROWS_IDENTICAL"] is True
    assert verification["SECOND_DRY_RUN_PROPOSED_INSERTS"] == 0

    # Idempotency: a fresh dry run proposes nothing.
    again = executor.preflight(manifest, store)
    assert len(again.proposed) == 0 and len(again.already_imported) == 2907

    # No asset / master API Plan mutation.
    assert _table_md5(seeded, "asset_registry", "asset_code") == assets_before
    assert _table_md5(seeded, "ltsa_pumps", "tag_number") == pumps_before

    # Tri-state leak, NULLs and the snapshot, as stored by Postgres.
    stored = {
        row["source_reference"]: row
        for row in store.rows_by_reference_or_code(
            [r.source_reference for r in manifest.rows], [r.reading_code for r in manifest.rows]
        )
    }
    leak_values = set()
    for row in manifest.rows:
        db_row = stored[row.source_reference]
        for name in executor.LEAK_FIELDS:
            assert db_row[name] is row.measurements[name]
            leak_values.add(db_row[name])
        for name, value in row.measurements.items():
            if value is None:
                assert db_row[name] is None
        assert db_row["api_plan_snapshot"] == row.api_plan_snapshot
    assert leak_values == {True, False, None}
    assert seeded.query_scalar(
        "SELECT count(*) FROM condition_monitoring_reading WHERE provenance = 'HISTORICAL_IMPORT' "
        "AND api_plan_snapshot = 'MASTER-PLAN-53B';"
    ) == "0"
