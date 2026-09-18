"""MWO-LTSA-REPORTING-R4 -- LtsaFindingRepository against a REAL,
disposable, published-port Postgres. Same container/bootstrap/truncate
pattern as test_ltsa_finding_and_cm_measurement_schema.py (R3).
"""

from __future__ import annotations

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
from API.ltsa_finding_repository import (  # noqa: E402
    AssetMismatch,
    ClosedRequiresClosedDate,
    InvalidSourceDomain,
    LtsaFindingRepository,
    SourceRecordNotFound,
)

_CONTAINER_NAME = "ai5r-test-ltsa-finding-repo-pg"
_USER = "ai5r"
_PASSWORD = "test-ltsa-finding-repo-password"
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

_HOC_ASSET = "211-P-13AR"       # area HOC
_HSC_ASSET = "212-P-25A"       # area HSC
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
        "TRUNCATE ltsa_finding, condition_monitoring_reading_measurement, condition_monitoring_reading, "
        "pm_occurrence, installation_report, asset_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area, status) VALUES "
        f"('{_HOC_ASSET}', '{_HOC_ASSET}', 'PUMP', 'HOC', 'Active'), "
        f"('{_HSC_ASSET}', '{_HSC_ASSET}', 'PUMP', 'HSC', 'Active');"
    )
    r.execute_script(
        "INSERT INTO condition_monitoring_reading "
        "(condition_monitoring_reading_code, condition_monitoring_schedule_code, asset_code, reading_date, workflow_status) "
        f"VALUES ('CMONR-1', 'UNSCHEDULED::test', '{_HOC_ASSET}', '2026-06-15', 'DRAFT');"
    )
    r.execute_script(
        "INSERT INTO pm_occurrence (pm_occurrence_code, pm_schedule_code, asset_code) VALUES "
        f"('PMOCC-1', 'SCHED-1', '{_HSC_ASSET}');"
    )
    r.execute_script(
        "INSERT INTO installation_report (installation_code, report_no, source_document_name, plant_equip_no) VALUES "
        f"('INSTL-1', 'RPT-1', 'test.pdf', '{_HOC_ASSET}'), "
        "('INSTL-2', 'RPT-2', 'test.pdf', 'UNRESOLVABLE-TAG-999');"
    )
    return r


@pytest.fixture
def repo(runner):
    return LtsaFindingRepository(runner)


# ---- create ----

def test_create_valid_finding(repo):
    created = repo.create(
        source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1",
        finding_text="leak observed", created_by=_ACTOR,
    )
    assert created["finding_code"].startswith("LTSAFND-")
    assert created["asset_code"] == _HOC_ASSET  # derived from source, not required from caller
    assert created["status"] is None
    assert created["severity"] is None


def test_null_status_and_severity_accepted(repo):
    created = repo.create(
        source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1",
        finding_text="x", created_by=_ACTOR,
    )
    assert created["status"] is None
    assert created["severity"] is None


@pytest.mark.parametrize("status", ["OPEN", "IN_PROGRESS", "CLOSED"])
def test_all_valid_status_values(repo, status):
    kwargs = {"closed_date": "2026-06-20"} if status == "CLOSED" else {}
    created = repo.create(
        source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1",
        finding_text="x", status=status, created_by=_ACTOR, **kwargs,
    )
    assert created["status"] == status


@pytest.mark.parametrize("severity", ["NORMAL", "ATTENTION", "CRITICAL"])
def test_all_valid_severity_values(repo, severity):
    created = repo.create(
        source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1",
        finding_text="x", severity=severity, created_by=_ACTOR,
    )
    assert created["severity"] == severity


def test_invalid_status_vocabulary_rejected(repo):
    with pytest.raises(psycopg2.Error):
        repo.create(
            source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1",
            finding_text="x", status="BOGUS", created_by=_ACTOR,
        )


def test_invalid_severity_vocabulary_rejected(repo):
    with pytest.raises(psycopg2.Error):
        repo.create(
            source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1",
            finding_text="x", severity="BOGUS", created_by=_ACTOR,
        )


def test_invalid_source_domain_rejected(repo):
    with pytest.raises(InvalidSourceDomain):
        repo.create(source_domain="CM_REPORT", source_record_code="X", finding_text="x", created_by=_ACTOR)


def test_nonexistent_source_rejected(repo):
    with pytest.raises(SourceRecordNotFound):
        repo.create(
            source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-DOES-NOT-EXIST",
            finding_text="x", created_by=_ACTOR,
        )


def test_multiple_findings_same_source_allowed(repo):
    repo.create(source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1", finding_text="a", created_by=_ACTOR)
    repo.create(source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1", finding_text="b", created_by=_ACTOR)
    result = repo.list_findings(source_record_code="CMONR-1")
    assert result["total"] == 2


def test_asset_mismatch_rejected(repo):
    with pytest.raises(AssetMismatch):
        repo.create(
            source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1",
            asset_code=_HSC_ASSET,  # CMONR-1 actually belongs to _HOC_ASSET
            finding_text="x", created_by=_ACTOR,
        )


def test_asset_consistent_supplied_value_accepted(repo):
    created = repo.create(
        source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1",
        asset_code=_HOC_ASSET, finding_text="x", created_by=_ACTOR,
    )
    assert created["asset_code"] == _HOC_ASSET


def test_installation_report_asset_derived_from_plant_equip_no(repo):
    created = repo.create(
        source_domain="INSTALLATION_REPORT", source_record_code="INSTL-1", finding_text="x", created_by=_ACTOR,
    )
    assert created["asset_code"] == _HOC_ASSET


def test_installation_report_unresolvable_plant_equip_no_falls_back_to_null_asset(repo):
    # plant_equip_no is disclosed (CANONICAL_SCHEMA.sql) as an informal
    # reference with no FK -- a value that does not match any real
    # asset_registry row must degrade to "no resolvable canonical asset"
    # (Chief's own R4 Section 5 fallback), never a bad asset_code.
    created = repo.create(
        source_domain="INSTALLATION_REPORT", source_record_code="INSTL-2", finding_text="x", created_by=_ACTOR,
    )
    assert created["asset_code"] is None


def test_closed_without_closed_date_rejected_on_create(repo):
    with pytest.raises(ClosedRequiresClosedDate):
        repo.create(
            source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1",
            finding_text="x", status="CLOSED", created_by=_ACTOR,
        )


# ---- list / filter ----

def test_list_by_source(repo):
    repo.create(source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1", finding_text="a", created_by=_ACTOR)
    repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="b", created_by=_ACTOR)
    result = repo.list_findings(source_domain="CONDITION_MONITORING_READING")
    assert result["total"] == 1


def test_list_by_asset(repo):
    repo.create(source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1", finding_text="a", created_by=_ACTOR)
    repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="b", created_by=_ACTOR)
    result = repo.list_findings(asset_code=_HOC_ASSET)
    assert result["total"] == 1
    assert result["data"][0]["asset_code"] == _HOC_ASSET


def test_filter_status(repo):
    repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="a", status="OPEN", created_by=_ACTOR)
    repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="b", created_by=_ACTOR)
    result = repo.list_findings(status="OPEN")
    assert result["total"] == 1


def test_filter_severity(repo):
    repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="a", severity="CRITICAL", created_by=_ACTOR)
    repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="b", created_by=_ACTOR)
    result = repo.list_findings(severity="CRITICAL")
    assert result["total"] == 1


def test_area_ma_scope_restriction(repo):
    repo.create(source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1", finding_text="a", created_by=_ACTOR)  # HOC
    repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="b", created_by=_ACTOR)  # HSC
    result = repo.list_findings(scope=frozenset({"HOC"}))
    assert result["total"] == 1
    assert result["data"][0]["asset_code"] == _HOC_ASSET


def test_empty_scope_excludes_everything(repo):
    repo.create(source_domain="CONDITION_MONITORING_READING", source_record_code="CMONR-1", finding_text="a", created_by=_ACTOR)
    result = repo.list_findings(scope=frozenset())
    assert result["total"] == 0


# ---- update ----

def test_update_finding_text(repo):
    created = repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="old", created_by=_ACTOR)
    updated = repo.update(created["finding_code"], values={"finding_text": "new"}, updated_by=_ACTOR)
    assert updated["finding_text"] == "new"
    assert updated["created_by"] == created["created_by"]  # audit fields preserved


def test_update_nonexistent_returns_none(repo):
    assert repo.update("LTSAFND-DOES-NOT-EXIST", values={"finding_text": "x"}, updated_by=_ACTOR) is None


def test_update_recommendation_and_action_independently(repo):
    created = repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="x", created_by=_ACTOR)
    updated = repo.update(created["finding_code"], values={"recommendation": "r", "action": "a"}, updated_by=_ACTOR)
    assert updated["recommendation"] == "r"
    assert updated["action"] == "a"


# ---- CLOSED semantics ----

def test_closed_without_closed_date_rejected_on_update(repo):
    created = repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="x", status="OPEN", created_by=_ACTOR)
    with pytest.raises(ClosedRequiresClosedDate):
        repo.update(created["finding_code"], values={"status": "CLOSED"}, updated_by=_ACTOR)


def test_closed_with_closed_date_accepted_on_update(repo):
    created = repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="x", status="OPEN", created_by=_ACTOR)
    updated = repo.update(
        created["finding_code"], values={"status": "CLOSED", "closed_date": "2026-06-20"}, updated_by=_ACTOR
    )
    assert updated["status"] == "CLOSED"
    assert updated["closed_date"] == "2026-06-20"


def test_status_change_away_from_closed_preserves_closed_date_unless_explicitly_changed(repo):
    created = repo.create(
        source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="x",
        status="CLOSED", closed_date="2026-06-20", created_by=_ACTOR,
    )
    # Reopen without mentioning closed_date at all -- historical close data
    # must survive untouched (Chief's own R4 Section 6 instruction: never
    # silently fabricate/delete it).
    updated = repo.update(created["finding_code"], values={"status": "IN_PROGRESS"}, updated_by=_ACTOR)
    assert updated["status"] == "IN_PROGRESS"
    assert updated["closed_date"] == "2026-06-20"


def test_no_automatic_severity_inference_on_update(repo):
    created = repo.create(source_domain="PM_OCCURRENCE", source_record_code="PMOCC-1", finding_text="x", created_by=_ACTOR)
    updated = repo.update(created["finding_code"], values={"status": "OPEN"}, updated_by=_ACTOR)
    assert updated["severity"] is None
