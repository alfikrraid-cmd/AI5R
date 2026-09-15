"""MWO-LTSA-REPORTING-R4 -- ConditionMonitoringMeasurementRepository
against a REAL, disposable, published-port Postgres. Same container/
bootstrap/truncate pattern as test_ltsa_finding_and_cm_measurement_schema.py
(R3)/test_ltsa_finding_repository.py (R4).
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.condition_monitoring_measurement_repository import (  # noqa: E402
    ConditionMonitoringMeasurementRepository,
    EmptyMeasurementValue,
)

_CONTAINER_NAME = "ai5r-test-cm-measurement-repo-pg"
_USER = "ai5r"
_PASSWORD = "test-cm-measurement-repo-password"
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

_HOC_ASSET = "211-P-13AR"
_HSC_ASSET = "212-P-25A"
_ACTOR = "00000000-0000-0000-0000-000000000001"


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
        "TRUNCATE condition_monitoring_reading_measurement, condition_monitoring_reading, "
        "asset_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area, status) VALUES "
        f"('{_HOC_ASSET}', '{_HOC_ASSET}', 'PUMP', 'HOC', 'Active'), "
        f"('{_HSC_ASSET}', '{_HSC_ASSET}', 'PUMP', 'HSC', 'Active');"
    )
    r.execute_script(
        "INSERT INTO condition_monitoring_reading "
        "(condition_monitoring_reading_code, condition_monitoring_schedule_code, asset_code, reading_date, workflow_status) "
        f"VALUES ('CMONR-HOC', 'UNSCHEDULED::test', '{_HOC_ASSET}', '2026-06-15', 'DRAFT'), "
        f"('CMONR-HSC', 'UNSCHEDULED::test', '{_HSC_ASSET}', '2026-06-15', 'DRAFT');"
    )
    return r


@pytest.fixture
def repo(runner):
    return ConditionMonitoringMeasurementRepository(runner)


# ---- create ----

def test_numeric_create_and_read(repo):
    created = repo.create(reading_id="CMONR-HOC", measurement_label="Separator Input Temp DE", measurement_code="SEP_IN_TEMP_DE", value_numeric=45.5, unit="C", created_by=_ACTOR)
    fetched = repo.find_by_id(created["measurement_id"])
    assert float(fetched["value_numeric"]) == 45.5
    assert fetched["value_text"] is None


def test_text_create_and_read(repo):
    created = repo.create(reading_id="CMONR-HOC", measurement_label="Temperature Gauge", value_text="Normal", created_by=_ACTOR)
    fetched = repo.find_by_id(created["measurement_id"])
    assert fetched["value_text"] == "Normal"
    assert fetched["value_numeric"] is None


def test_literal_source_label_round_trip(repo):
    literal = "QUENCH IN (unresolved -- verbatim)"
    created = repo.create(
        reading_id="CMONR-HOC", measurement_label="Quench In (pending review)",
        value_text="observed", source_label=literal, verification_status="UNDER_REVIEW", created_by=_ACTOR,
    )
    fetched = repo.find_by_id(created["measurement_id"])
    assert fetched["source_label"] == literal
    assert fetched["measurement_code"] is None
    assert fetched["verification_status"] == "UNDER_REVIEW"


def test_measurement_code_null_supported(repo):
    created = repo.create(reading_id="CMONR-HOC", measurement_label="x", value_text="y", created_by=_ACTOR)
    assert created["measurement_code"] is None


def test_invalid_parent_rejected(repo):
    assert repo.create(reading_id="CMONR-DOES-NOT-EXIST", measurement_label="x", value_text="y", created_by=_ACTOR) is None


def test_empty_value_rejected(repo):
    with pytest.raises(EmptyMeasurementValue):
        repo.create(reading_id="CMONR-HOC", measurement_label="x", created_by=_ACTOR)


# ---- update ----

def test_update_value(repo):
    created = repo.create(reading_id="CMONR-HOC", measurement_label="x", value_numeric=1, created_by=_ACTOR)
    updated = repo.update(created["measurement_id"], values={"value_numeric": 2}, updated_by=_ACTOR)
    assert float(updated["value_numeric"]) == 2


def test_update_nonexistent_returns_none(repo):
    assert repo.update("00000000-0000-0000-0000-000000000099", values={"value_numeric": 1}, updated_by=_ACTOR) is None


def test_update_to_empty_value_rejected(repo):
    created = repo.create(reading_id="CMONR-HOC", measurement_label="x", value_numeric=1, created_by=_ACTOR)
    with pytest.raises(EmptyMeasurementValue):
        repo.update(created["measurement_id"], values={"value_numeric": None}, updated_by=_ACTOR)


def test_update_verification_status(repo):
    created = repo.create(reading_id="CMONR-HOC", measurement_label="x", value_numeric=1, created_by=_ACTOR)
    updated = repo.update(created["measurement_id"], values={"verification_status": "VERIFIED"}, updated_by=_ACTOR)
    assert updated["verification_status"] == "VERIFIED"


def test_invalid_verification_status_rejected_by_db(repo):
    import psycopg2
    created = repo.create(reading_id="CMONR-HOC", measurement_label="x", value_numeric=1, created_by=_ACTOR)
    with pytest.raises(psycopg2.Error):
        repo.update(created["measurement_id"], values={"verification_status": "BOGUS"}, updated_by=_ACTOR)


# ---- list by reading ----

def test_list_by_reading(repo):
    repo.create(reading_id="CMONR-HOC", measurement_label="a", value_numeric=1, created_by=_ACTOR)
    repo.create(reading_id="CMONR-HOC", measurement_label="b", value_numeric=2, created_by=_ACTOR)
    repo.create(reading_id="CMONR-HSC", measurement_label="c", value_numeric=3, created_by=_ACTOR)
    rows = repo.list_by_reading("CMONR-HOC")
    assert len(rows) == 2


def test_list_by_reading_nonexistent_returns_none(repo):
    assert repo.list_by_reading("CMONR-DOES-NOT-EXIST") is None


# ---- area/MA scope ----

def test_list_by_reading_area_scope_restriction(repo):
    repo.create(reading_id="CMONR-HOC", measurement_label="a", value_numeric=1, created_by=_ACTOR)
    rows_in_scope = repo.list_by_reading("CMONR-HOC", scope=frozenset({"HOC"}))
    rows_out_of_scope = repo.list_by_reading("CMONR-HOC", scope=frozenset({"HSC"}))
    assert len(rows_in_scope) == 1
    assert len(rows_out_of_scope) == 0
