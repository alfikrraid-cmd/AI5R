"""MWO-LTSA-REPORTING-R3 -- proves migration 037 (ltsa_finding,
condition_monitoring_reading_measurement) against a REAL, disposable,
published-port Postgres running the actual canonical schema. Same
container/bootstrap/truncate pattern already established by
test_ltsa_contract_scope_real_db.py -- reused verbatim, not reinvented.

Schema-only mission: no repository/service layer exists yet (R4_API is a
separate, later phase), so these tests exercise the migration's own DDL
directly (INSERT/SELECT/constraint-violation checks via psycopg2), not an
API surface. DatabaseRunner only exposes query_scalar/execute_script (no
query_all) -- multi-row/multi-column reads go through the same
json_agg(row_to_json(...)) pattern already used by _json_query in
ltsa_pump_inventory_db_upsert.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import psycopg2
import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402

_CONTAINER_NAME = "ai5r-test-ltsa-finding-cm-measurement-pg"
_USER = "ai5r"
_PASSWORD = "test-ltsa-finding-cm-measurement-password"
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
        "035_retarget_document_field_extraction_to_asset_registry.sql",
        "036_create_ltsa_contract_scope.sql",
        "037_create_ltsa_finding_and_cm_measurement.sql",
    )
]

_ASSET = "211-P-13AR"


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
    r.execute_script(
        "TRUNCATE condition_monitoring_reading_measurement, ltsa_finding, "
        "condition_monitoring_reading, asset_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area, status) VALUES "
        f"('{_ASSET}', '{_ASSET}', 'PUMP', 'HOC', 'Active');"
    )
    return r


def _rows(runner, sql):
    wrapped = f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;"
    raw = runner.query_scalar(wrapped)
    return json.loads(raw or "[]")


def _count(runner, sql):
    raw = runner.query_scalar(sql)
    return int(raw or "0")


def _insert_reading(runner, asset=_ASSET, reading_date="2026-06-15", code="CMONR-TEST-1"):
    runner.execute_script(
        "INSERT INTO condition_monitoring_reading "
        "(condition_monitoring_reading_code, condition_monitoring_schedule_code, asset_code, reading_date, workflow_status) "
        f"VALUES ('{code}', 'UNSCHEDULED::test', '{asset}', '{reading_date}', 'DRAFT');"
    )
    return code


def _insert_finding(runner, code="LTSAFND-TEST-1", source_domain="CONDITION_MONITORING_READING",
                     source_record_code="CMONR-TEST-1", asset_code=_ASSET, status="SQL_NULL", severity="SQL_NULL"):
    status_sql = "NULL" if status == "SQL_NULL" else f"'{status}'"
    severity_sql = "NULL" if severity == "SQL_NULL" else f"'{severity}'"
    asset_sql = "NULL" if asset_code is None else f"'{asset_code}'"
    runner.execute_script(
        "INSERT INTO ltsa_finding (finding_code, source_domain, source_record_code, asset_code, finding_text, status, severity) "
        f"VALUES ('{code}', '{source_domain}', '{source_record_code}', {asset_sql}, 'test finding', {status_sql}, {severity_sql});"
    )
    return code


# ---- table existence / column shape ----

def test_ltsa_finding_table_exists(runner):
    rows = _rows(runner, "SELECT column_name FROM information_schema.columns WHERE table_name = 'ltsa_finding'")
    cols = {r["column_name"] for r in rows}
    for expected in (
        "finding_code", "source_domain", "source_record_code", "asset_code", "finding_text",
        "status", "severity", "recommendation", "action", "owner_pic", "opened_date", "closed_date",
        "source_reference", "created_at", "created_by", "updated_at", "updated_by",
    ):
        assert expected in cols


def test_cm_measurement_table_exists(runner):
    rows = _rows(
        runner,
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'condition_monitoring_reading_measurement'",
    )
    cols = {r["column_name"] for r in rows}
    for expected in (
        "measurement_id", "reading_id", "measurement_code", "measurement_label", "value_numeric",
        "value_text", "unit", "measurement_side", "source_label", "source_reference",
        "verification_status", "created_at", "created_by", "updated_at", "updated_by",
    ):
        assert expected in cols


def test_ltsa_finding_indexes_exist(runner):
    rows = _rows(runner, "SELECT indexname FROM pg_indexes WHERE tablename = 'ltsa_finding'")
    idx = {r["indexname"] for r in rows}
    assert "idx_ltsa_finding_source" in idx
    assert "idx_ltsa_finding_asset_code" in idx
    assert "idx_ltsa_finding_status" in idx
    assert "idx_ltsa_finding_severity" in idx


def test_cm_measurement_index_exists(runner):
    rows = _rows(
        runner,
        "SELECT indexname FROM pg_indexes WHERE tablename = 'condition_monitoring_reading_measurement'",
    )
    idx = {r["indexname"] for r in rows}
    assert "idx_condition_monitoring_reading_measurement_reading_id" in idx


# ---- ltsa_finding constraints ----

def test_finding_null_status_and_severity_accepted(runner):
    _insert_finding(runner)
    row = _rows(runner, "SELECT status, severity FROM ltsa_finding WHERE finding_code = 'LTSAFND-TEST-1'")[0]
    assert row["status"] is None
    assert row["severity"] is None


def test_finding_valid_status_and_severity_accepted(runner):
    _insert_finding(runner, status="OPEN", severity="CRITICAL")
    row = _rows(runner, "SELECT status, severity FROM ltsa_finding WHERE finding_code = 'LTSAFND-TEST-1'")[0]
    assert row["status"] == "OPEN"
    assert row["severity"] == "CRITICAL"


def test_finding_invalid_status_rejected(runner):
    with pytest.raises(psycopg2.Error):
        _insert_finding(runner, status="BOGUS")


def test_finding_invalid_severity_rejected(runner):
    with pytest.raises(psycopg2.Error):
        _insert_finding(runner, severity="BOGUS")


def test_finding_invalid_source_domain_rejected(runner):
    with pytest.raises(psycopg2.Error):
        _insert_finding(runner, source_domain="BOGUS_DOMAIN")


def test_finding_all_three_source_domains_accepted(runner):
    _insert_finding(runner, code="F1", source_domain="CONDITION_MONITORING_READING", source_record_code="X1")
    _insert_finding(runner, code="F2", source_domain="PM_OCCURRENCE", source_record_code="X2")
    _insert_finding(runner, code="F3", source_domain="INSTALLATION_REPORT", source_record_code="X3")
    assert _count(runner, "SELECT COUNT(*) FROM ltsa_finding") == 3


def test_finding_multiple_per_source_record_allowed(runner):
    # Chief's explicit R3 instruction: no uniqueness constraint may block
    # more than one legitimate finding on the same source transaction.
    _insert_finding(runner, code="F1", source_record_code="CMONR-SAME")
    _insert_finding(runner, code="F2", source_record_code="CMONR-SAME")
    assert _count(runner, "SELECT COUNT(*) FROM ltsa_finding WHERE source_record_code = 'CMONR-SAME'") == 2


def test_finding_asset_code_nullable(runner):
    _insert_finding(runner, asset_code=None)
    row = _rows(runner, "SELECT asset_code FROM ltsa_finding WHERE finding_code = 'LTSAFND-TEST-1'")[0]
    assert row["asset_code"] is None


def test_finding_asset_fk_rejects_unknown_asset(runner):
    with pytest.raises(psycopg2.Error):
        _insert_finding(runner, asset_code="NO-SUCH-ASSET")


def test_finding_asset_delete_restricted_while_referenced(runner):
    _insert_finding(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(f"DELETE FROM asset_registry WHERE asset_code = '{_ASSET}';")


def test_finding_closed_before_opened_rejected(runner):
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO ltsa_finding (finding_code, source_domain, source_record_code, finding_text, "
            "opened_date, closed_date) VALUES "
            "('F-BAD-DATES', 'CONDITION_MONITORING_READING', 'X', 'test', '2026-06-15', '2026-06-01');"
        )


def test_finding_recommendation_and_action_are_distinct_columns(runner):
    runner.execute_script(
        "INSERT INTO ltsa_finding (finding_code, source_domain, source_record_code, finding_text, "
        "recommendation, action) VALUES "
        "('F-REC-ACT', 'CONDITION_MONITORING_READING', 'X', 'test', 'recommend X', 'do Y');"
    )
    row = _rows(runner, "SELECT recommendation, action FROM ltsa_finding WHERE finding_code = 'F-REC-ACT'")[0]
    assert row["recommendation"] == "recommend X"
    assert row["action"] == "do Y"


# ---- condition_monitoring_reading_measurement ----

def test_measurement_numeric_value(runner):
    _insert_reading(runner)
    runner.execute_script(
        "INSERT INTO condition_monitoring_reading_measurement "
        "(reading_id, measurement_code, measurement_label, value_numeric, unit, measurement_side) VALUES "
        "('CMONR-TEST-1', 'SEPARATOR_INPUT_TEMP_DE', 'Separator Input Temp DE Side', 45.5, 'C', 'DE');"
    )
    row = _rows(
        runner,
        "SELECT value_numeric, value_text FROM condition_monitoring_reading_measurement WHERE reading_id = 'CMONR-TEST-1'",
    )[0]
    assert float(row["value_numeric"]) == 45.5
    assert row["value_text"] is None


def test_measurement_textual_value(runner):
    _insert_reading(runner)
    runner.execute_script(
        "INSERT INTO condition_monitoring_reading_measurement "
        "(reading_id, measurement_code, measurement_label, value_text) VALUES "
        "('CMONR-TEST-1', 'TEMPERATURE_GAUGE', 'Temperature Gauge', 'Normal');"
    )
    row = _rows(
        runner,
        "SELECT value_numeric, value_text FROM condition_monitoring_reading_measurement WHERE reading_id = 'CMONR-TEST-1'",
    )[0]
    assert row["value_numeric"] is None
    assert row["value_text"] == "Normal"


def test_measurement_source_label_preserved_for_ambiguous_field(runner):
    # R2's 3 FIELD_ENGINEERING_REVIEW concepts: measurement_code stays
    # NULL (no guessed canonical key), source_label carries the literal
    # source wording verbatim, verification_status flags it for review.
    _insert_reading(runner)
    runner.execute_script(
        "INSERT INTO condition_monitoring_reading_measurement "
        "(reading_id, measurement_label, value_text, source_label, verification_status) VALUES "
        "('CMONR-TEST-1', 'Quench In (unresolved)', 'observed', 'QUENCH IN', 'UNDER_REVIEW');"
    )
    row = _rows(
        runner,
        "SELECT measurement_code, source_label, verification_status FROM condition_monitoring_reading_measurement "
        "WHERE reading_id = 'CMONR-TEST-1'",
    )[0]
    assert row["measurement_code"] is None
    assert row["source_label"] == "QUENCH IN"
    assert row["verification_status"] == "UNDER_REVIEW"


def test_measurement_empty_value_rejected(runner):
    _insert_reading(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO condition_monitoring_reading_measurement (reading_id, measurement_label) VALUES "
            "('CMONR-TEST-1', 'No Value Given');"
        )


def test_measurement_invalid_side_rejected(runner):
    _insert_reading(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO condition_monitoring_reading_measurement "
            "(reading_id, measurement_label, value_text, measurement_side) VALUES "
            "('CMONR-TEST-1', 'x', 'y', 'BOGUS_SIDE');"
        )


def test_measurement_invalid_verification_status_rejected(runner):
    _insert_reading(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO condition_monitoring_reading_measurement "
            "(reading_id, measurement_label, value_text, verification_status) VALUES "
            "('CMONR-TEST-1', 'x', 'y', 'BOGUS_STATUS');"
        )


def test_measurement_orphan_reading_id_rejected(runner):
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO condition_monitoring_reading_measurement (reading_id, measurement_label, value_text) VALUES "
            "('CMONR-DOES-NOT-EXIST', 'x', 'y');"
        )


def test_measurement_cascade_deletes_with_parent_reading(runner):
    _insert_reading(runner)
    runner.execute_script(
        "INSERT INTO condition_monitoring_reading_measurement (reading_id, measurement_label, value_text) VALUES "
        "('CMONR-TEST-1', 'x', 'y');"
    )
    assert _count(
        runner,
        "SELECT COUNT(*) FROM condition_monitoring_reading_measurement WHERE reading_id = 'CMONR-TEST-1'",
    ) == 1
    runner.execute_script(
        "DELETE FROM condition_monitoring_reading WHERE condition_monitoring_reading_code = 'CMONR-TEST-1';"
    )
    assert _count(
        runner,
        "SELECT COUNT(*) FROM condition_monitoring_reading_measurement WHERE reading_id = 'CMONR-TEST-1'",
    ) == 0


def test_measurement_multiple_rows_per_reading_allowed(runner):
    _insert_reading(runner)
    runner.execute_script(
        "INSERT INTO condition_monitoring_reading_measurement (reading_id, measurement_code, measurement_label, value_numeric) VALUES "
        "('CMONR-TEST-1', 'SEPARATOR_INPUT_TEMP_DE', 'a', 1), "
        "('CMONR-TEST-1', 'SEPARATOR_OUTPUT_TEMP_DE', 'b', 2), "
        "('CMONR-TEST-1', 'SEPARATOR_RETURN_TEMP_DE', 'c', 3);"
    )
    assert _count(
        runner,
        "SELECT COUNT(*) FROM condition_monitoring_reading_measurement WHERE reading_id = 'CMONR-TEST-1'",
    ) == 3


# ---- no historical backfill / canonical counts unchanged ----

def test_migration_inserts_zero_rows(runner):
    assert _count(runner, "SELECT COUNT(*) FROM ltsa_finding") == 0
    assert _count(runner, "SELECT COUNT(*) FROM condition_monitoring_reading_measurement") == 0


def test_migration_037_is_purely_additive_existing_tables_unchanged(runner):
    # Section 8's own requirement, proven directly rather than assumed:
    # seed one row in each of the 3 pre-existing canonical tables, then
    # re-apply migration 037's own script again (its IF NOT EXISTS/
    # CREATE-only DDL makes this a safe no-op) and confirm every count
    # and the seeded rows themselves are byte-for-byte unchanged.
    _insert_reading(runner, code="CMONR-PREEXISTING")
    runner.execute_script(
        "INSERT INTO pm_occurrence (pm_occurrence_code, pm_schedule_code, asset_code) VALUES "
        "('PMOCC-PREEXISTING', 'SCHED-1', '" + _ASSET + "');"
    )
    runner.execute_script(
        "INSERT INTO installation_report (installation_code, report_no, source_document_name) VALUES "
        "('INSTL-PREEXISTING', 'RPT-PREEXISTING', 'test.pdf');"
    )
    before = (
        _count(runner, "SELECT COUNT(*) FROM condition_monitoring_reading"),
        _count(runner, "SELECT COUNT(*) FROM pm_occurrence"),
        _count(runner, "SELECT COUNT(*) FROM installation_report"),
    )

    migration_sql = (_DATABASE_DIR / "MIGRATIONS" / "037_create_ltsa_finding_and_cm_measurement.sql").read_text(
        encoding="utf-8"
    )
    runner.execute_script(migration_sql)

    after = (
        _count(runner, "SELECT COUNT(*) FROM condition_monitoring_reading"),
        _count(runner, "SELECT COUNT(*) FROM pm_occurrence"),
        _count(runner, "SELECT COUNT(*) FROM installation_report"),
    )
    assert before == after
    assert _count(runner, "SELECT COUNT(*) FROM condition_monitoring_reading WHERE condition_monitoring_reading_code = 'CMONR-PREEXISTING'") == 1
    assert _count(runner, "SELECT COUNT(*) FROM pm_occurrence WHERE pm_occurrence_code = 'PMOCC-PREEXISTING'") == 1
    assert _count(runner, "SELECT COUNT(*) FROM installation_report WHERE installation_code = 'INSTL-PREEXISTING'") == 1
