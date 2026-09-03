"""PM CANONICAL WRITER REPAIR -- proves the repaired PMOccurrenceRepository.
create_draft() against a REAL, disposable, published-port Postgres running
the actual canonical schema -- the same real-schema discipline
PRODUCTS/LTSA-BRAIN/INGESTION/TEST/test_installation_fitment_migration.py's
own header, and this session's own
CORE-SERVICES/BACKEND-API/TESTS/test_whatsapp_cmon_writer_real_db.py,
already established.

This is the regression the prior FakeRunner-only test suite
(test_pm_occurrence_repository.py) could never catch: a real SQL syntax
error (SQLSTATE 42601, stray "VALUES" before an INSERT...SELECT, plus a
misplaced RETURNING clause) that failed on every single call regardless of
payload, but is invisible to any test that only inspects the SQL text a
FakeRunner recorded rather than executing it.
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
_BACKEND_API_DIR = _CORE_SERVICES_DIR / "BACKEND-API"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR, _BACKEND_API_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.pm_occurrence_repository import PMOccurrenceRepository  # noqa: E402
from API.condition_monitoring_reading_repository import ConditionMonitoringReadingRepository  # noqa: E402
from API.historical_pm_cmon_promotion_service import promote_pm_occurrence_atomic  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from dependencies import get_current_user, get_pm_occurrence_repository  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

_CONTAINER_NAME = "ai5r-test-pm-occurrence-writer-pg"
_USER = "ai5r"
_PASSWORD = "test-pm-occurrence-writer-password"
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
    )
]

_ASSET_CODE = "211-P-13AR"
_SCHEDULE_CODE = "PMSCHED-REAL-1"
_ACTOR = "11111111-1111-1111-1111-111111111111"


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
        "TRUNCATE pm_occurrence, pm_schedule, condition_monitoring_reading, condition_monitoring_schedule, "
        "record_change_history, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_ASSET_CODE}', 'HOC');")
    r.execute_script(
        f"INSERT INTO pm_schedule (pm_schedule_code, asset_code, asset_type, procedure, frequency, trigger_type, status) "
        f"VALUES ('{_SCHEDULE_CODE}', '{_ASSET_CODE}', 'PUMP', 'Lubrication', 'Monthly', 'TIME_BASED', 'ACTIVE');"
    )
    return r


@pytest.fixture
def pm_repo(runner):
    return PMOccurrenceRepository(runner)


def test_create_draft_writes_exactly_one_canonical_occurrence(pm_repo):
    # Requirements 1-3, 5: exactly one row, returned code matches stored
    # code, every supplied field maps correctly, source_reference preserved.
    created = pm_repo.create_draft(
        pm_schedule_code=_SCHEDULE_CODE,
        asset_code=_ASSET_CODE,
        asset_type="PUMP",
        occurrence_date="2026-08-29",
        activities=[{"description": "Lubrication check", "done": True}],
        remarks="routine PM visit",
        created_by=_ACTOR,
        provenance="MANUAL",
        source_reference="document_field_extraction:test-candidate-1",
    )

    assert created["asset_code"] == _ASSET_CODE
    assert created["asset_type"] == "PUMP"
    assert created["occurrence_date"].startswith("2026-08-29")
    assert created["activities"] == [{"description": "Lubrication check", "done": True}]
    assert created["remarks"] == "routine PM visit"
    assert created["provenance"] == "MANUAL"
    assert created["workflow_status"] == "DRAFT"
    assert created["created_by"] == _ACTOR
    assert created["updated_by"] == _ACTOR
    assert created["source_reference"] == "document_field_extraction:test-candidate-1"
    assert created["pm_schedule_code"] == _SCHEDULE_CODE

    stored = pm_repo.find_by_code(created["pm_occurrence_code"])
    assert stored is not None
    assert stored["pm_occurrence_code"] == created["pm_occurrence_code"]

    all_rows = pm_repo.list_by_asset(_ASSET_CODE)
    assert len(all_rows) == 1


def test_create_draft_audit_and_schedule_completion_behavior(pm_repo, runner):
    # Requirement 4: audit/history behavior exactly as existing design --
    # one CREATE audit row for the occurrence, one status-change audit row
    # for the schedule, and the schedule itself auto-completes (existing
    # MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 behavior, unchanged by this fix).
    created = pm_repo.create_draft(
        pm_schedule_code=_SCHEDULE_CODE,
        asset_code=_ASSET_CODE,
        asset_type="PUMP",
        occurrence_date="2026-08-29",
        activities=None,
        remarks=None,
        created_by=_ACTOR,
    )

    import json
    audit_rows = json.loads(
        runner.query_scalar(
            "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ("
            "SELECT entity_type, entity_id, field_name, reason FROM record_change_history "
            "ORDER BY changed_at) t;"
        )
    )
    assert len(audit_rows) == 2
    occurrence_audit = next(r for r in audit_rows if r["entity_type"] == "PM_OCCURRENCE")
    assert occurrence_audit["entity_id"] == created["pm_occurrence_code"]
    assert occurrence_audit["field_name"] == "__record__"
    assert occurrence_audit["reason"] == "CREATE"
    schedule_audit = next(r for r in audit_rows if r["entity_type"] == "PM_SCHEDULE")
    assert schedule_audit["entity_id"] == _SCHEDULE_CODE
    assert schedule_audit["field_name"] == "status"
    assert schedule_audit["reason"] == "AUTO_COMPLETE_ON_OCCURRENCE"

    schedule_status = json.loads(
        runner.query_scalar(
            f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM "
            f"(SELECT status FROM pm_schedule WHERE pm_schedule_code = 'PMSCHED-REAL-1') t;"
        )
    )
    assert schedule_status[0]["status"] == "COMPLETED"


def test_create_draft_repeated_calls_create_separate_occurrences_no_repository_level_dedup(pm_repo):
    # Requirement 6: PM's create_draft has NO source_reference-based
    # idempotency check of its own (unlike CMON's WhatsApp writer, whose
    # dedup lives in the SERVICE layer above the repository, not inside
    # create_draft/create_ad_hoc_draft themselves). A second call with the
    # same source_reference legitimately creates a SECOND, separate
    # canonical record -- this is EXISTING PM semantics, not invented here.
    first = pm_repo.create_draft(
        pm_schedule_code=_SCHEDULE_CODE, asset_code=_ASSET_CODE, asset_type="PUMP",
        occurrence_date="2026-08-29", activities=None, remarks=None, created_by=_ACTOR,
        source_reference="document_field_extraction:test-candidate-1",
    )
    second = pm_repo.create_draft(
        pm_schedule_code=_SCHEDULE_CODE, asset_code=_ASSET_CODE, asset_type="PUMP",
        occurrence_date="2026-08-29", activities=None, remarks=None, created_by=_ACTOR,
        source_reference="document_field_extraction:test-candidate-1",
    )

    assert first["pm_occurrence_code"] != second["pm_occurrence_code"]
    all_rows = pm_repo.list_by_asset(_ASSET_CODE)
    assert len(all_rows) == 2


def test_create_draft_nonexistent_schedule_rejected_as_designed(pm_repo):
    # Requirement 7: invalid schedule/reference behavior remains rejected
    # exactly as designed -- the WHERE EXISTS gate matches zero rows, and
    # create_draft's existing (unchanged) contract is to raise IndexError
    # on rows[0] of an empty result, same as condition_monitoring_reading_
    # repository.create_draft's own identical contract.
    with pytest.raises(IndexError):
        pm_repo.create_draft(
            pm_schedule_code="PMSCHED-DOES-NOT-EXIST", asset_code=_ASSET_CODE, asset_type="PUMP",
            occurrence_date="2026-08-29", activities=None, remarks=None, created_by=_ACTOR,
        )
    assert pm_repo.list_by_asset(_ASSET_CODE) == []


def test_create_draft_nonexistent_pump_rejected_as_designed(pm_repo):
    with pytest.raises(IndexError):
        pm_repo.create_draft(
            pm_schedule_code=_SCHEDULE_CODE, asset_code="999-P-99", asset_type="PUMP",
            occurrence_date="2026-08-29", activities=None, remarks=None, created_by=_ACTOR,
        )


def test_create_draft_never_affects_cmon_records(pm_repo, runner):
    # Requirement 8: no CMON records are affected by the PM writer repair.
    pm_repo.create_draft(
        pm_schedule_code=_SCHEDULE_CODE, asset_code=_ASSET_CODE, asset_type="PUMP",
        occurrence_date="2026-08-29", activities=None, remarks=None, created_by=_ACTOR,
    )
    cmon_repo = ConditionMonitoringReadingRepository(runner)
    assert cmon_repo.list_by_asset(_ASSET_CODE) == []


# --- Phase 5: real callers, through the actual repaired repository ------

client = TestClient(app)


def _identity(role: str = "TAP_ENGINEER", user_id: str = _ACTOR) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal", username="field.operator",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=None, data_scope_value=None,
    )


def test_dashboard_create_route_reaches_repaired_repository_and_persists(pm_repo):
    # Phase 5A -- the real dashboard/API PM create path, through the
    # actual FastAPI route, with the real (now-repaired) repository bound
    # to real Postgres. Proves the route reaches create_draft and a real
    # canonical row lands, not just that the repository method works in
    # isolation.
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _identity()
    app.dependency_overrides[get_pm_occurrence_repository] = lambda: pm_repo
    try:
        response = client.post(
            "/api/ltsa/pm-occurrences",
            json={
                "pm_schedule_code": _SCHEDULE_CODE,
                "asset_code": _ASSET_CODE,
                "asset_type": "PUMP",
                "occurrence_date": "2026-08-29",
                "remarks": "dashboard-created",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["remarks"] == "dashboard-created"
    assert data["created_by"] == _ACTOR  # the authenticated actor, never spoofable from the body

    stored = pm_repo.find_by_code(data["pm_occurrence_code"])
    assert stored is not None
    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 1


def test_dashboard_create_route_diagnostic_logs_on_failure_without_changing_response(pm_repo, caplog):
    # The Phase 3 diagnostic addition, verified without changing existing
    # behavior: create_draft's existing (unchanged) contract raises
    # IndexError on a genuinely nonexistent schedule -- the route does not
    # catch this as a clean 404 (a pre-existing gap, unchanged here, and
    # explicitly not "fixed" as part of this repair since that would be
    # redesigning caller behavior beyond the SQL grammar repair). Starlette's
    # TestClient (raise_server_exceptions=True, its default) re-raises an
    # unhandled route exception into the caller rather than returning a 500
    # response -- proving this is truly unchanged from before the repair.
    # What IS new: a safe, non-payload diagnostic line logs before the
    # exception propagates.
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _identity()
    app.dependency_overrides[get_pm_occurrence_repository] = lambda: pm_repo
    try:
        with caplog.at_level("INFO"):
            with pytest.raises(IndexError):
                client.post(
                    "/api/ltsa/pm-occurrences",
                    json={"pm_schedule_code": "PMSCHED-DOES-NOT-EXIST", "asset_code": _ASSET_CODE},
                )
    finally:
        app.dependency_overrides.clear()

    log_lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("event=pm_occurrence_write")]
    assert len(log_lines) == 1
    assert "result=FAILED" in log_lines[0]
    assert "exception_class=IndexError" in log_lines[0]
    # Never the request payload/asset code in the diagnostic line.
    assert _ASSET_CODE not in log_lines[0]


def test_historical_promotion_reaches_repaired_repository_and_persists(pm_repo, runner):
    # MWO-LTSA-ATOMIC-PM-PROMOTION-001 -- the atomic historical promotion
    # path, through the real (unmodified) promote_pm_occurrence_atomic,
    # with the real repository bound to real Postgres. Unlike the old
    # promote_pm_occurrence_candidate (which took a plain Python dict),
    # the atomic path re-reads the candidate from document_field_
    # extraction itself, so a real row must exist first.
    import json as _json

    runner.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, "
        "detected_document_type, extraction_provider, extracted_fields, reviewed_fields, "
        "status, pump_tag_number) VALUES ("
        "'dfe-real-db-1', 'PDF-REAL-DB-1', 'PDF', 'HISTORICAL_PM_OCCURRENCE_CANDIDATE', "
        "'deterministic_workbook_table_parser', '{}'::jsonb, "
        f"'{_json.dumps({'asset_type': 'PUMP', 'occurrence_date': '2026-08-29', 'activities': [{'description': 'Lubrication check', 'done': True}], 'remarks': 'promoted from historical import'})}'::jsonb, "
        f"'REVIEWED', '{_ASSET_CODE}');"
    )

    record = promote_pm_occurrence_atomic(
        "dfe-real-db-1",
        pm_occurrence_repository=pm_repo,
        pm_schedule_code=_SCHEDULE_CODE,
        promoted_by=_ACTOR,
    )

    assert record["provenance"] == "HISTORICAL_IMPORT"
    assert record["source_reference"] == "document_field_extraction:dfe-real-db-1"
    assert record["remarks"] == "promoted from historical import"

    stored = pm_repo.find_by_code(record["pm_occurrence_code"])
    assert stored is not None
    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 1

    staged = runner.query_scalar(
        "SELECT status FROM document_field_extraction WHERE document_field_extraction_id = 'dfe-real-db-1'"
    )
    assert staged == "SAVED"

    # Retry proof: a second promotion attempt against the SAME real row
    # must be recognized as already-promoted, never a duplicate write.
    from API.historical_pm_cmon_promotion_service import AlreadyPromotedError
    with pytest.raises(AlreadyPromotedError):
        promote_pm_occurrence_atomic(
            "dfe-real-db-1",
            pm_occurrence_repository=pm_repo,
            pm_schedule_code=_SCHEDULE_CODE,
            promoted_by=_ACTOR,
        )
    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 1


# --- MWO: PM ad-hoc / unscheduled canonical write -----------------------

def test_ad_hoc_zero_schedules_writes_exactly_one_occurrence_no_fake_schedule(pm_repo, runner):
    # Requirements 1-3: zero open schedules -> exactly one pm_occurrence,
    # pm_schedule table stays at zero rows, sentinel stored exactly as
    # designed (UNSCHEDULED::<provenance>, never a fabricated schedule row).
    # The `runner` fixture seeds one ACTIVE schedule by default (used by
    # the real-schedule tests above) -- cleared here for a genuinely
    # empty pm_schedule table.
    runner.execute_script("DELETE FROM pm_schedule;")
    assert pm_repo.find_open_schedules_by_asset(_ASSET_CODE) == []

    created = pm_repo.create_ad_hoc_draft(
        asset_code=_ASSET_CODE,
        asset_type="PUMP",
        occurrence_date="2026-08-29",
        activities=[{"description": "Ad-hoc lubrication", "done": True}],
        remarks="unscheduled visit",
        created_by=_ACTOR,
        source_reference="WHATSAPP::test-intake-1",
        provenance="WHATSAPP",
    )

    assert created is not None
    assert created["pm_schedule_code"] == "UNSCHEDULED::WHATSAPP"
    assert created["asset_code"] == _ASSET_CODE
    assert created["remarks"] == "unscheduled visit"
    assert created["source_reference"] == "WHATSAPP::test-intake-1"
    assert created["provenance"] == "WHATSAPP"
    assert created["workflow_status"] == "DRAFT"

    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 1
    schedule_count = runner.query_scalar("SELECT count(*) FROM pm_schedule")
    assert schedule_count == "0"


def test_ad_hoc_create_audit_exists_no_schedule_audit(pm_repo, runner):
    # Requirements 4-5: PM occurrence CREATE audit exists; no PM_SCHEDULE
    # AUTO_COMPLETE_ON_OCCURRENCE audit event -- there is no real schedule
    # to complete or audit.
    created = pm_repo.create_ad_hoc_draft(
        asset_code=_ASSET_CODE, asset_type="PUMP", occurrence_date="2026-08-29",
        activities=None, remarks=None, created_by=_ACTOR,
        source_reference="WHATSAPP::test-intake-2",
    )

    import json
    audit_rows = json.loads(
        runner.query_scalar(
            "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM "
            "(SELECT entity_type, entity_id, reason FROM record_change_history) t;"
        )
    )
    assert len(audit_rows) == 1
    assert audit_rows[0]["entity_type"] == "PM_OCCURRENCE"
    assert audit_rows[0]["entity_id"] == created["pm_occurrence_code"]
    assert audit_rows[0]["reason"] == "CREATE"
    assert not any(row["entity_type"] == "PM_SCHEDULE" for row in audit_rows)


def test_real_schedule_path_still_works_alongside_ad_hoc(pm_repo, runner):
    # Requirement 6: the pre-existing real-schedule path (create_draft)
    # is unaffected by adding create_ad_hoc_draft alongside it. The
    # `runner` fixture already seeds _SCHEDULE_CODE as ACTIVE.
    real = pm_repo.create_draft(
        pm_schedule_code=_SCHEDULE_CODE, asset_code=_ASSET_CODE, asset_type="PUMP",
        occurrence_date="2026-08-29", activities=None, remarks=None, created_by=_ACTOR,
    )
    assert real["pm_schedule_code"] == _SCHEDULE_CODE
    schedule_status = runner.query_scalar(
        f"SELECT status FROM pm_schedule WHERE pm_schedule_code = '{_SCHEDULE_CODE}'"
    )
    assert schedule_status == "COMPLETED"  # real-schedule auto-completion still fires


def test_ad_hoc_nonexistent_pump_returns_none_not_exception(pm_repo):
    # Requirement 7: invalid/nonexistent pump rejected according to
    # EXISTING semantics -- create_ad_hoc_draft's contract mirrors
    # condition_monitoring_reading_repository.create_ad_hoc_draft's own
    # (returns None, no exception), distinct from create_draft's own
    # IndexError-on-gate-failure contract (that method is unchanged).
    result = pm_repo.create_ad_hoc_draft(
        asset_code="999-P-99", asset_type="PUMP", occurrence_date="2026-08-29",
        activities=None, remarks=None, created_by=_ACTOR,
        source_reference="WHATSAPP::test-intake-3",
    )
    assert result is None


def test_ad_hoc_never_affects_cmon_records(pm_repo, runner):
    # Requirement 8: no CMON records are affected.
    pm_repo.create_ad_hoc_draft(
        asset_code=_ASSET_CODE, asset_type="PUMP", occurrence_date="2026-08-29",
        activities=None, remarks=None, created_by=_ACTOR,
        source_reference="WHATSAPP::test-intake-4",
    )
    cmon_repo = ConditionMonitoringReadingRepository(runner)
    assert cmon_repo.list_by_asset(_ASSET_CODE) == []


def test_terminal_only_schedules_treated_as_zero_open(pm_repo, runner):
    # Requirement 9: a schedule that exists but is CANCELLED/COMPLETED is
    # correctly treated as "no open schedule" -- find_open_schedules_by_
    # asset excludes it, matching create_draft's own auto-completion
    # eligibility semantics exactly. Clears the fixture's default ACTIVE
    # schedule first so only the two terminal ones below are present.
    runner.execute_script("DELETE FROM pm_schedule;")
    runner.execute_script(
        f"INSERT INTO pm_schedule (pm_schedule_code, asset_code, asset_type, procedure, frequency, trigger_type, status) "
        f"VALUES ('PMSCHED-DONE', '{_ASSET_CODE}', 'PUMP', 'Lubrication', 'Monthly', 'TIME_BASED', 'COMPLETED'), "
        f"('PMSCHED-CANCEL', '{_ASSET_CODE}', 'PUMP', 'Inspection', 'Weekly', 'TIME_BASED', 'CANCELLED');"
    )

    assert pm_repo.find_open_schedules_by_asset(_ASSET_CODE) == []

    created = pm_repo.create_ad_hoc_draft(
        asset_code=_ASSET_CODE, asset_type="PUMP", occurrence_date="2026-08-29",
        activities=None, remarks=None, created_by=_ACTOR,
        source_reference="WHATSAPP::test-intake-5",
    )
    assert created["pm_schedule_code"] == "UNSCHEDULED::WHATSAPP"


def test_multiple_open_schedules_reported_for_future_resolver(pm_repo, runner):
    # Requirement 10: find_open_schedules_by_asset (the repository-level
    # query a future clarification resolver would act on -- no service-
    # layer resolver exists yet, per this MWO's own Phase 6 GO/NO-GO scope)
    # correctly reports ALL open schedules when more than one exists, never
    # silently picking one.
    runner.execute_script("DELETE FROM pm_schedule;")
    runner.execute_script(
        f"INSERT INTO pm_schedule (pm_schedule_code, asset_code, asset_type, procedure, frequency, trigger_type, status) "
        f"VALUES ('PMSCHED-A', '{_ASSET_CODE}', 'PUMP', 'Lubrication', 'Monthly', 'TIME_BASED', 'ACTIVE'), "
        f"('PMSCHED-B', '{_ASSET_CODE}', 'PUMP', 'Inspection', 'Weekly', 'TIME_BASED', 'PLANNED');"
    )

    open_schedules = pm_repo.find_open_schedules_by_asset(_ASSET_CODE)
    assert {s["pm_schedule_code"] for s in open_schedules} == {"PMSCHED-A", "PMSCHED-B"}
    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 0  # nothing written -- ambiguity, no guess
