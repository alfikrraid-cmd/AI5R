"""LTSA_CONDITION_MONITORING_SAFE_DRAFT_DELETE_R2 -- proves the Chief-
approved Condition Monitoring Reading delete policy against a REAL,
disposable Postgres running the canonical schema (same pg_port/
DatabaseRunner/bootstrap_schema fixture shape as
test_whatsapp_cmon_writer_real_db.py). A Fake runner can only prove the
SQL text; only a real database proves the guarded UPDATE actually refuses
a non-deletable row, that the row physically survives, that the reason
reaches record_change_history, and that normal read paths and analytics
stop seeing a soft-deleted reading.

Policy: soft delete only, and only when workflow_status='DRAFT' AND
deleted_at IS NULL AND provenance IS DISTINCT FROM 'HISTORICAL_IMPORT',
for every role holding maintenance.write -- SUPERUSER included.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_BACKEND_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _BACKEND_API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_BACKEND_API_DIR, _CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.condition_monitoring_reading_repository import ConditionMonitoringReadingRepository  # noqa: E402
from API.ltsa_analytics_service import LTSAAnalyticsService  # noqa: E402
from dependencies import get_condition_monitoring_reading_repository, get_current_user  # noqa: E402
from main import app  # noqa: E402

_CONTAINER_NAME = "ai5r-test-cmon-delete-draft-pg"
_USER = "ai5r"
_PASSWORD = "test-cmon-delete-draft-password"
_DATABASE = "ltsa_brain"
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATIONS = [
    _DATABASE_DIR / "MIGRATIONS" / name
    for name in (
        "006_ltsa_pumps_add_name_criticality.sql",
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
        "018_create_seal_unit.sql",
        "019_create_seal_lifecycle_event.sql",
        "023_create_pm_cmon_base_tables_for_legacy_upgrade.sql",
        "027_add_pm_cmon_soft_delete.sql",
        "028_add_schedule_attribution_soft_delete.sql",
        "029_add_condition_monitoring_schedule_lifecycle.sql",
        "038_add_cmon_api_plan_snapshot.sql",
    )
]

_ACTOR = "33333333-3333-3333-3333-333333333333"
_PUMP = "211-P-TEST"

# code -> (workflow_status, provenance, already soft-deleted)
_SEED = {
    "CMONR-DRAFT": ("DRAFT", "MANUAL", False),
    "CMONR-DRAFT-WA": ("DRAFT", "WHATSAPP", False),
    "CMONR-HIST": ("DRAFT", "HISTORICAL_IMPORT", False),
    "CMONR-RFC": ("RETURNED_FOR_CORRECTION", "MANUAL", False),
    "CMONR-SUB": ("SUBMITTED", "MANUAL", False),
    "CMONR-FIN": ("FINALIZED", "MANUAL", False),
    "CMONR-GONE": ("DRAFT", "MANUAL", True),
}


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
        # Test-DB-only accommodation for TD-020: get_executive_analytics()
        # filters work_order.work_type, which no CANONICAL_SCHEMA/migration file
        # defines (pre-existing, recorded in CHANGELOG; not part of this change).
        probe.execute_script("ALTER TABLE work_order ADD COLUMN IF NOT EXISTS work_type TEXT;")
        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script(
        "TRUNCATE condition_monitoring_reading, record_change_history, pm_occurrence, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO ltsa_pumps (tag_number, area, pump_type, api_plan) VALUES ('{_PUMP}', 'HOC', 'OH2', '53A');"
    )
    for code, (status, provenance, deleted) in _SEED.items():
        deleted_sql = f"NOW(), '{_ACTOR}'" if deleted else "NULL, NULL"
        r.execute_script(
            "INSERT INTO condition_monitoring_reading (condition_monitoring_reading_code, "
            "condition_monitoring_schedule_code, asset_code, asset_type, reading_date, mechanical_seal_leak_de, "
            "workflow_status, provenance, created_by, deleted_at, deleted_by) VALUES "
            f"('{code}', 'UNSCHEDULED::MANUAL', '{_PUMP}', 'PUMP', '2026-08-29', true, "
            f"'{status}', '{provenance}', '{_ACTOR}', {deleted_sql});"
        )
    return r


@pytest.fixture
def api(runner):
    repo = ConditionMonitoringReadingRepository(runner)

    def _as(role: str):
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedIdentity(
            user_id=_ACTOR, email="actor@tap.internal", organization_id="org-tap", organization_code="TAP",
            role=role, permissions=ROLE_PERMISSIONS[role],
        )
        app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: repo
        return TestClient(app)

    yield _as
    app.dependency_overrides.clear()


def _delete(client, code, reason="Entered by mistake"):
    return client.request("DELETE", f"/api/ltsa/condition-monitoring-readings/{code}", json={"reason": reason})


def _row(runner, code):
    rows = json.loads(runner.query_scalar(
        "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM (SELECT workflow_status, deleted_at, deleted_by "
        f"FROM condition_monitoring_reading WHERE condition_monitoring_reading_code = '{code}') t;"
    ) or "[]")
    return rows[0] if rows else None


def _audit_rows(runner, code):
    return json.loads(runner.query_scalar(
        "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM (SELECT entity_type, field_name, old_value, "
        f"new_value, changed_by, reason FROM record_change_history WHERE entity_id = '{code}') t;"
    ) or "[]")


# A / B -- maintenance.write roles delete an ordinary DRAFT (MANUAL or WHATSAPP).
@pytest.mark.parametrize("role", ["TAP_ADMIN", "TAP_ENGINEER"])
@pytest.mark.parametrize("code", ["CMONR-DRAFT", "CMONR-DRAFT-WA"])
def test_maintenance_write_role_soft_deletes_an_ordinary_draft(api, runner, role, code):
    response = _delete(api(role), code)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["condition_monitoring_reading_code"] == code
    assert _row(runner, code)["deleted_at"] is not None


# C -- no maintenance.write -> 403, nothing written.
def test_role_without_maintenance_write_gets_403_and_nothing_changes(api, runner):
    assert _delete(api("JOHN_CRANE_ENGINEER"), "CMONR-DRAFT").status_code == 403
    assert _row(runner, "CMONR-DRAFT")["deleted_at"] is None
    assert _audit_rows(runner, "CMONR-DRAFT") == []


# D / E / F / G / H -- guard enforced in the write itself, for every role.
@pytest.mark.parametrize("role", ["TAP_ENGINEER", "TAP_ADMIN", "SUPERUSER"])
@pytest.mark.parametrize("code", ["CMONR-HIST", "CMONR-RFC", "CMONR-SUB", "CMONR-FIN"])
def test_non_deletable_reading_is_409_and_untouched_for_every_role(api, runner, role, code):
    before = _row(runner, code)
    response = _delete(api(role), code)
    assert response.status_code == 409
    assert _row(runner, code) == before
    assert before["deleted_at"] is None
    assert _audit_rows(runner, code) == []


# I -- already deleted cannot be deleted again (pre-deleted and delete-twice).
def test_already_deleted_reading_is_409(api, runner):
    client = api("SUPERUSER")
    before = _row(runner, "CMONR-GONE")
    response = _delete(client, "CMONR-GONE")
    assert response.status_code == 409
    assert "already deleted" in response.json()["detail"]
    assert _row(runner, "CMONR-GONE") == before

    assert _delete(client, "CMONR-DRAFT").status_code == 200
    first_deleted_at = _row(runner, "CMONR-DRAFT")["deleted_at"]
    assert _delete(client, "CMONR-DRAFT").status_code == 409
    assert _row(runner, "CMONR-DRAFT")["deleted_at"] == first_deleted_at
    assert len(_audit_rows(runner, "CMONR-DRAFT")) == 1


def test_unknown_reading_is_404(api):
    assert _delete(api("TAP_ADMIN"), "CMONR-NOPE").status_code == 404


# J / K / L -- reason persisted, full snapshot kept, row physically present.
def test_delete_persists_reason_snapshot_and_keeps_the_row(api, runner):
    count_before = runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading")
    assert _delete(api("TAP_ENGINEER"), "CMONR-DRAFT", reason="Duplicate of CMONR-X").status_code == 200

    assert runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading") == count_before
    row = _row(runner, "CMONR-DRAFT")
    assert row["deleted_at"] is not None
    assert row["deleted_by"] == _ACTOR
    assert row["workflow_status"] == "DRAFT"

    audit = _audit_rows(runner, "CMONR-DRAFT")
    assert len(audit) == 1
    assert audit[0]["entity_type"] == "CONDITION_MONITORING_READING"
    assert audit[0]["field_name"] == "__record__"
    assert audit[0]["reason"] == "Duplicate of CMONR-X"
    assert audit[0]["changed_by"] == _ACTOR
    assert audit[0]["new_value"] is None
    snapshot = json.loads(audit[0]["old_value"])
    assert snapshot["condition_monitoring_reading_code"] == "CMONR-DRAFT"
    assert snapshot["deleted_at"] is None


# M / N -- normal list, detail and Asset360 (list_by_asset) exclude it.
def test_normal_read_paths_exclude_the_deleted_reading(api, runner):
    client = api("TAP_ENGINEER")
    assert _delete(client, "CMONR-DRAFT").status_code == 200
    repo = ConditionMonitoringReadingRepository(runner)

    listed = client.get("/api/ltsa/condition-monitoring-readings?limit=100").json()
    listed_codes = {r["condition_monitoring_reading_code"] for r in listed["items"]}
    assert "CMONR-DRAFT" not in listed_codes
    assert "CMONR-GONE" not in listed_codes
    assert listed_codes == {"CMONR-DRAFT-WA", "CMONR-HIST", "CMONR-RFC", "CMONR-SUB", "CMONR-FIN"}
    assert listed["total"] == 5

    assert client.get("/api/ltsa/condition-monitoring-readings/CMONR-DRAFT").status_code == 404
    assert repo.find_by_code("CMONR-DRAFT") is None
    assert "CMONR-DRAFT" not in {r["condition_monitoring_reading_code"] for r in repo.list_by_asset(_PUMP)}


# O -- analytics exclude soft-deleted readings (all seeded readings leak DE).
def test_analytics_exclude_deleted_readings(api, runner):
    analytics = LTSAAnalyticsService(runner)
    # 6 active readings seeded (CMONR-GONE is pre-deleted).
    assert analytics.get_maintenance_effectiveness()["metrics"]["confirmed_leaks"] == 6
    executive = analytics.get_executive_analytics()
    assert executive["kpis"]["confirmed_seal_leaks"] == 6

    assert _delete(api("TAP_ENGINEER"), "CMONR-DRAFT").status_code == 200

    effectiveness = analytics.get_maintenance_effectiveness()
    assert effectiveness["metrics"]["confirmed_leaks"] == 5
    assert sum(a["leak_count"] for a in effectiveness["area_effectiveness"]) == 5

    executive = analytics.get_executive_analytics()
    assert executive["kpis"]["confirmed_seal_leaks"] == 5
    assert executive["kpis"]["de_leaks"] == 5
    assert sum(d["cmon_readings"] for d in executive["trends"]["daily"]) == 5
    assert sum(a["cmon_readings"] for a in executive["area_breakdown"]) == 5
    assert executive["top_bad_actors"][0]["leak_count"] == 5

    seal = analytics.get_seal_analytics()
    assert sum(r["leak_count"] for r in seal["leaks_by_pump_type"]) == 5
    assert sum(r["leak_count"] for r in seal["leaks_by_api_plan"]) == 5
