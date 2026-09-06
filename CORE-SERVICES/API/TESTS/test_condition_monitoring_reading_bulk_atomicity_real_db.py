"""MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- proves
ConditionMonitoringReadingRepository.create_ad_hoc_batch() is genuinely
atomic against a REAL, disposable Postgres running the actual canonical
schema (same discipline as test_pm_occurrence_repository_real_db.py /
test_pm_occurrence_repository_real_db.py's own header) -- a Fake-runner
test can prove the router's *contract* (a raised exception yields no
success response), but only a real database can prove Postgres itself
rolled back every row when one row in a 10-row batch is invalid, since
that guarantee lives entirely in the DO-block-precheck + single implicit
transaction, not in any Python-level logic this repository owns.

NOTE (environment): this file was written and reviewed but NOT executed
in the authoring session -- Docker Desktop was unavailable throughout
(`docker ps` failed with "failed to connect to the docker API"). It
follows the exact same pg_port/DatabaseRunner/bootstrap_schema fixture
shape as test_pm_occurrence_repository_real_db.py, which HAS run
successfully in this environment historically, so the fixture itself is
not new/unproven -- only this specific test run could not be confirmed
this session. Run it before relying on this atomicity guarantee in
production.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
_BACKEND_API_DIR = _CORE_SERVICES_DIR / "BACKEND-API"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR, _BACKEND_API_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.condition_monitoring_reading_repository import ConditionMonitoringReadingRepository  # noqa: E402

_CONTAINER_NAME = "ai5r-test-cmon-bulk-atomicity-pg"
_USER = "ai5r"
_PASSWORD = "test-cmon-bulk-atomicity-password"
_DATABASE = "ltsa_brain"
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
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

_ACTOR = "22222222-2222-2222-2222-222222222222"
_N = 10


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _CONTAINER_NAME,
            "-e", f"POSTGRES_USER={_USER}",
            "-e", f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e", f"POSTGRES_DB={_DATABASE}",
            "-p", "127.0.0.1::5432",
            "postgres:16-alpine",
        ],
        check=True, capture_output=True, text=True,
    )
    try:
        port_output = subprocess.run(
            ["docker", "port", _CONTAINER_NAME, "5432/tcp"], check=True, capture_output=True, text=True,
        ).stdout.strip()
        host_port = int(port_output.rsplit(":", 1)[1])

        probe = DatabaseRunner(
            DatabaseConfig(host="127.0.0.1", port=host_port, user=_USER, password=_PASSWORD, database=_DATABASE)
        )
        last_error: Exception | None = None
        for _ in range(30):
            try:
                probe.query_scalar("SELECT 1")
                last_error = None
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                import time
                time.sleep(1)
        if last_error is not None:
            raise RuntimeError(f"Test Postgres never became ready: {last_error}")

        bootstrap_schema(probe, _SCHEMA_FILE)
        for migration in _MIGRATIONS:
            bootstrap_schema(probe, migration)

        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script("TRUNCATE condition_monitoring_reading, record_change_history, ltsa_pumps RESTART IDENTITY CASCADE;")
    for i in range(_N):
        r.execute_script(f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('PUMP-REAL-{i}', 'HOC');")
    return r


def _row(i, *, bad_pump=False):
    tag = "PUMP-DOES-NOT-EXIST" if bad_pump else f"PUMP-REAL-{i}"
    return {
        "asset_code": tag,
        "asset_type": "PUMP",
        "reading_date": "2026-09-06",
        "measurements": {"mechseal_temp_de": 70.0 + i, "mechseal_temp_nde": None},
        "finding": None,
        "source_reference": f"MANUAL_WEB:test-{i}",
    }


def test_ten_valid_rows_creates_exactly_ten_readings_and_ten_audit_rows(runner):
    repo = ConditionMonitoringReadingRepository(runner)
    pre_readings = int(runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading") or "0")
    pre_audit = int(
        runner.query_scalar(
            "SELECT count(*) FROM record_change_history WHERE entity_type='CONDITION_MONITORING_READING' AND reason='CREATE'"
        )
        or "0"
    )
    assert pre_readings == 0 and pre_audit == 0

    rows = [_row(i) for i in range(_N)]
    created = repo.create_ad_hoc_batch(rows, created_by=_ACTOR)
    assert len(created) == _N

    post_readings = int(runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading") or "0")
    post_audit = int(
        runner.query_scalar(
            "SELECT count(*) FROM record_change_history WHERE entity_type='CONDITION_MONITORING_READING' AND reason='CREATE'"
        )
        or "0"
    )
    assert post_readings == _N
    assert post_audit == _N

    codes = [r["condition_monitoring_reading_code"] for r in created]
    assert len(set(codes)) == _N  # no duplicate code

    for r in created:
        assert r["workflow_status"] == "DRAFT"
        assert r["provenance"] == "MANUAL"
        assert r["condition_monitoring_schedule_code"] == "UNSCHEDULED::MANUAL"


# MWO-LTSA-CMON-EXCEL-IMPORT-001, Section 10 -- closes Phase 4F.3's own
# disclosed residual gap: explicit numeric 0 and leak tri-state
# (null/false/true) were proven at the Fake/pure-function level, but
# never independently re-verified against a REAL Postgres round trip.
# This test changes no repository behavior -- it only reads back what
# the SAME create_ad_hoc_batch() already persists, via a fresh raw SQL
# SELECT (never trusting the returned JSON alone), for six
# representative rows covering every case the gap named.
def test_explicit_zero_and_leak_tristate_persist_correctly_against_real_postgres(runner):
    repo = ConditionMonitoringReadingRepository(runner)
    rows = [
        {  # DE-only
            "asset_code": "PUMP-REAL-0", "asset_type": "PUMP", "reading_date": "2026-09-06",
            "measurements": {"mechseal_temp_de": 75.2, "mechseal_temp_nde": None},
            "finding": None, "source_reference": "MANUAL_WEB:sem-0",
        },
        {  # NDE-only
            "asset_code": "PUMP-REAL-1", "asset_type": "PUMP", "reading_date": "2026-09-06",
            "measurements": {"mechseal_temp_de": None, "mechseal_temp_nde": 68.0},
            "finding": None, "source_reference": "MANUAL_WEB:sem-1",
        },
        {  # DE + NDE
            "asset_code": "PUMP-REAL-2", "asset_type": "PUMP", "reading_date": "2026-09-06",
            "measurements": {"mechseal_temp_de": 70.0, "mechseal_temp_nde": 65.0},
            "finding": None, "source_reference": "MANUAL_WEB:sem-2",
        },
        {  # explicit numeric 0 (suction_pressure)
            "asset_code": "PUMP-REAL-3", "asset_type": "PUMP", "reading_date": "2026-09-06",
            "measurements": {"suction_pressure": 0},
            "finding": None, "source_reference": "MANUAL_WEB:sem-3",
        },
        {  # leak DE=false, NDE=null (not recorded)
            "asset_code": "PUMP-REAL-4", "asset_type": "PUMP", "reading_date": "2026-09-06",
            "measurements": {"mechanical_seal_leak_de": False, "mechanical_seal_leak_nde": None},
            "finding": None, "source_reference": "MANUAL_WEB:sem-4",
        },
        {  # leak DE=true, NDE=false
            "asset_code": "PUMP-REAL-5", "asset_type": "PUMP", "reading_date": "2026-09-06",
            "measurements": {"mechanical_seal_leak_de": True, "mechanical_seal_leak_nde": False},
            "finding": None, "source_reference": "MANUAL_WEB:sem-5",
        },
    ]
    created = repo.create_ad_hoc_batch(rows, created_by=_ACTOR)
    assert len(created) == 6
    codes_sql = ", ".join(f"'{r['condition_monitoring_reading_code']}'" for r in created)

    # Re-read directly from the table -- never trust the returned JSON
    # alone as proof of what was actually persisted.
    raw = runner.query_scalar(
        "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ("
        "SELECT condition_monitoring_reading_code, asset_code, mechseal_temp_de, mechseal_temp_nde, "
        "suction_pressure, mechanical_seal_leak_de, mechanical_seal_leak_nde "
        f"FROM condition_monitoring_reading WHERE condition_monitoring_reading_code IN ({codes_sql})"
        ") t"
    )
    persisted = {row["asset_code"]: row for row in json.loads(raw)}

    de_only = persisted["PUMP-REAL-0"]
    assert de_only["mechseal_temp_de"] == 75.2
    assert de_only["mechseal_temp_nde"] is None

    nde_only = persisted["PUMP-REAL-1"]
    assert nde_only["mechseal_temp_de"] is None
    assert nde_only["mechseal_temp_nde"] == 68.0

    both = persisted["PUMP-REAL-2"]
    assert both["mechseal_temp_de"] == 70.0
    assert both["mechseal_temp_nde"] == 65.0

    explicit_zero = persisted["PUMP-REAL-3"]
    assert explicit_zero["suction_pressure"] == 0
    assert explicit_zero["suction_pressure"] is not None  # 0 persists as 0, never coerced to NULL

    leak_false_row = persisted["PUMP-REAL-4"]
    assert leak_false_row["mechanical_seal_leak_de"] is False
    assert leak_false_row["mechanical_seal_leak_nde"] is None
    assert leak_false_row["mechanical_seal_leak_de"] is not leak_false_row["mechanical_seal_leak_nde"]  # NULL != FALSE

    leak_true_row = persisted["PUMP-REAL-5"]
    assert leak_true_row["mechanical_seal_leak_de"] is True
    assert leak_true_row["mechanical_seal_leak_nde"] is False

    # No hidden measurement values: every column not explicitly set on a
    # given row stays NULL.
    assert persisted["PUMP-REAL-0"]["mechanical_seal_leak_de"] is None
    assert persisted["PUMP-REAL-3"]["mechseal_temp_de"] is None


def test_one_bad_pump_in_ten_rolls_back_the_entire_batch_zero_writes(runner):
    repo = ConditionMonitoringReadingRepository(runner)
    rows = [_row(i) for i in range(_N - 1)] + [_row(_N - 1, bad_pump=True)]

    with pytest.raises(Exception):  # noqa: B017 -- DB driver exception type varies; real Postgres RAISE EXCEPTION from the precheck DO block
        repo.create_ad_hoc_batch(rows, created_by=_ACTOR)

    post_readings = int(runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading") or "0")
    post_audit = int(
        runner.query_scalar(
            "SELECT count(*) FROM record_change_history WHERE entity_type='CONDITION_MONITORING_READING' AND reason='CREATE'"
        )
        or "0"
    )
    assert post_readings == 0  # READINGS_CREATED=0
    assert post_audit == 0  # AUDITS_CREATED=0


def test_corrected_retry_after_failed_batch_creates_all_ten_with_unique_codes(runner):
    repo = ConditionMonitoringReadingRepository(runner)
    bad_rows = [_row(i) for i in range(_N - 1)] + [_row(_N - 1, bad_pump=True)]
    with pytest.raises(Exception):  # noqa: B017
        repo.create_ad_hoc_batch(bad_rows, created_by=_ACTOR)

    good_rows = [_row(i) for i in range(_N)]
    created = repo.create_ad_hoc_batch(good_rows, created_by=_ACTOR)

    assert len(created) == _N
    post_readings = int(runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading") or "0")
    assert post_readings == _N  # the failed attempt left nothing behind to collide with the retry
    codes = [r["condition_monitoring_reading_code"] for r in created]
    assert len(set(codes)) == _N


def test_bulk_create_has_zero_side_effects_on_schedules_and_pm(runner):
    repo = ConditionMonitoringReadingRepository(runner)
    pre_schedules = int(runner.query_scalar("SELECT count(*) FROM condition_monitoring_schedule") or "0")
    pre_pm_occ = int(runner.query_scalar("SELECT count(*) FROM pm_occurrence") or "0")
    pre_pm_sched = int(runner.query_scalar("SELECT count(*) FROM pm_schedule") or "0")

    repo.create_ad_hoc_batch([_row(i) for i in range(_N)], created_by=_ACTOR)

    assert int(runner.query_scalar("SELECT count(*) FROM condition_monitoring_schedule") or "0") == pre_schedules
    assert int(runner.query_scalar("SELECT count(*) FROM pm_occurrence") or "0") == pre_pm_occ
    assert int(runner.query_scalar("SELECT count(*) FROM pm_schedule") or "0") == pre_pm_sched
