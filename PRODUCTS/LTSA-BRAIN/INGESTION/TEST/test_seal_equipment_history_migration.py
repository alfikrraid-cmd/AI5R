"""MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- proves
seal_equipment_history_service.py's pump/seal-unit timeline aggregation
against a REAL, disposable, published-port Postgres. Pure read-model:
no new migration, no new persistence -- this file bootstraps through
migration 022 (unchanged from #6.5) since this MWO adds ZERO schema.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

_INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

_REPO_ROOT = _INGESTION_PATH.parents[2]
_CORE_SERVICES_PATH = _REPO_ROOT / "CORE-SERVICES"
if str(_CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(_CORE_SERVICES_PATH))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.seal_unit_repository import SealUnitRepository  # noqa: E402
from API.seal_lifecycle_service import apply_lifecycle_event, SealLifecycleEventRepository  # noqa: E402
from API.seal_inspection_service import create_inspection, SealInspectionRepository  # noqa: E402
from API.seal_repair_service import create_repair, SealRepairRepository  # noqa: E402
from API.seal_warranty_service import create_warranty_assessment, SealWarrantyAssessmentRepository  # noqa: E402
from API.installation_fitment_service import (  # noqa: E402
    link_installation_report,
    InstallationReportFitmentRepository,
)
from API.seal_equipment_history_service import (  # noqa: E402
    build_seal_events_for_pump,
    build_seal_unit_history,
    linked_installation_codes_for_pump,
)
from API.timeline_value_objects import TimelineCategory  # noqa: E402

_CONTAINER_NAME = "ai5r-test-seal-equipment-history-pg"
_USER = "ai5r"
_PASSWORD = "test-seal-equipment-history-password"
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
        "018_create_seal_unit.sql",
        "019_create_seal_lifecycle_event.sql",
        "020_create_seal_inspection_repair.sql",
        "021_create_seal_warranty_assessment.sql",
        "022_alter_installation_report_installation_event_link.sql",
    )
]

_SEAL_CODE = "JC-TYPE-X"
_PUMP_A = "110-P-9A"
_PUMP_B = "211-P-1A"
_ACTOR = "test-actor-1"


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
        "TRUNCATE installation_report, seal_warranty_assessment, seal_repair, seal_inspection_finding, "
        "seal_inspection, seal_lifecycle_event, seal_unit, seal_pump_compatibility, seal_stock, "
        "seal_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_PUMP_A}', 'HOC'), ('{_PUMP_B}', 'HCC');"
        f"INSERT INTO seal_registry (seal_code, seal_name) VALUES ('{_SEAL_CODE}', 'Type X');"
    )
    return r


@pytest.fixture
def repos(runner):
    return {
        "seal_lifecycle_event_repository": SealLifecycleEventRepository(runner),
        "seal_inspection_repository": SealInspectionRepository(runner),
        "seal_repair_repository": SealRepairRepository(runner),
        "seal_warranty_assessment_repository": SealWarrantyAssessmentRepository(runner),
        "installation_report_fitment_repository": InstallationReportFitmentRepository(runner),
    }


@pytest.fixture
def seal_unit(runner):
    return SealUnitRepository(runner).create(seal_code=_SEAL_CODE)


def _create_report(runner, *, code, report_no):
    from ltsa_pump_inventory_db_upsert import _sql
    runner.execute_script(
        "INSERT INTO installation_report (installation_code, report_no, source_document_name) "
        f"VALUES ({_sql(code)}, {_sql(report_no)}, {_sql('doc.pdf')});"
    )
    return code


def _types(events):
    return [e.event_type for e in events]


# --- 3/4: INSTALL appears once; linked report does not duplicate --------

def test_install_appears_once_and_carries_linked_report_as_evidence(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    install = apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    code = _create_report(runner, code="INST-A", report_no="RPT-A")
    link_installation_report(runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"], pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR)

    events = build_seal_events_for_pump(_PUMP_A, **repos)
    installs = [e for e in events if e.event_type == TimelineCategory.SEAL_INSTALL]
    assert len(installs) == 1
    assert installs[0].payload["installation_report"]["installation_code"] == code

    linked_codes = linked_installation_codes_for_pump(_PUMP_A, installation_report_fitment_repository=repos["installation_report_fitment_repository"])
    assert code in linked_codes


def test_install_without_any_report_remains_valid(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    events = build_seal_events_for_pump(_PUMP_A, **repos)
    installs = [e for e in events if e.event_type == TimelineCategory.SEAL_INSTALL]
    assert len(installs) == 1
    assert installs[0].payload["installation_report"] is None


# --- 5/6/7: REMOVE historical pump preserved; reinstall A->B; current_pump never rewrites ---

def test_reinstall_pump_a_to_pump_b_histories_are_correct_and_independent(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="RETURN_TO_STOCK", event_at="2026-02-02T00:00:00Z", created_by=_ACTOR)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-03-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_B)

    unit_after = SealUnitRepository(runner).find_by_id(uid)
    assert unit_after["current_pump_tag_number"] == _PUMP_B

    pump_a_events = build_seal_events_for_pump(_PUMP_A, **repos)
    pump_b_events = build_seal_events_for_pump(_PUMP_B, **repos)

    assert _types(pump_a_events) == [TimelineCategory.SEAL_INSTALL, TimelineCategory.SEAL_REMOVE]
    assert _types(pump_b_events) == [TimelineCategory.SEAL_INSTALL]
    # current_pump moving to B must never have moved E1/REMOVE into B's history.
    assert all(e.payload["pump_tag_number"] == _PUMP_A for e in pump_a_events)
    assert all(e.payload["pump_tag_number"] == _PUMP_B for e in pump_b_events)


# --- 8/9: pump inspection appears; pumpless inspection not assigned -----

def test_pump_scoped_inspection_appears_pumpless_inspection_does_not(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    create_inspection(runner, seal_unit_id=uid, inspection_date="2026-02-02T00:00:00Z", inspection_type="POST_REMOVAL", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    create_inspection(runner, seal_unit_id=uid, inspection_date="2026-02-03T00:00:00Z", inspection_type="GENERAL", created_by=_ACTOR)  # pumpless

    events = build_seal_events_for_pump(_PUMP_A, **repos)
    inspections = [e for e in events if e.event_type == TimelineCategory.SEAL_INSPECTION]
    assert len(inspections) == 1
    assert inspections[0].payload["pump_tag_number"] == _PUMP_A


# --- 10/11: repair derives pump only through linked inspection ----------

def test_repair_appears_in_pump_timeline_only_via_linked_inspection_pump(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    inspection = create_inspection(runner, seal_unit_id=uid, inspection_date="2026-02-02T00:00:00Z", inspection_type="PRE_REPAIR", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="SEND_FOR_REPAIR", event_at="2026-02-03T00:00:00Z", created_by=_ACTOR, reason="x")
    create_repair(runner, seal_unit_id=uid, inspection_id=inspection["inspection_id"], repair_date="2026-02-04T00:00:00Z", repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR)
    # A second repair with NO linked inspection at all -- must never be
    # fabricated into pump A's timeline.
    create_repair(runner, seal_unit_id=uid, repair_date="2026-02-05T00:00:00Z", repair_type="B", repair_action="y", created_by=_ACTOR)

    pump_a_events = build_seal_events_for_pump(_PUMP_A, **repos)
    repairs = [e for e in pump_a_events if e.event_type == TimelineCategory.SEAL_REPAIR]
    assert len(repairs) == 1
    assert repairs[0].payload["pump_tag_number"] == _PUMP_A

    # Seal-unit history still shows BOTH repairs (never fabricated into a
    # pump, but always part of the unit's own complete history).
    unit_history = build_seal_unit_history(uid, **repos)
    unit_repairs = [e for e in unit_history if e.event_type == TimelineCategory.SEAL_REPAIR]
    assert len(unit_repairs) == 2


# --- 12/13: warranty pump derives from INSTALL event; window != decision -

def test_warranty_pump_derives_from_install_event_and_window_differs_from_decision(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    install = apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    create_warranty_assessment(runner, seal_unit_id=uid, installation_event_id=install["event_id"], created_by=_ACTOR, failure_date="2026-06-01T00:00:00Z")

    events = build_seal_events_for_pump(_PUMP_A, **repos)
    warranties = [e for e in events if e.event_type == TimelineCategory.SEAL_WARRANTY]
    assert len(warranties) == 1
    w = warranties[0]
    assert w.payload["pump_tag_number"] == _PUMP_A
    assert w.payload["window_status"] == "WITHIN_WARRANTY_WINDOW"
    assert w.payload["decision_status"] == "PENDING_EXAMINATION"
    assert w.payload["window_status"] != w.payload["decision_status"]


# --- 14: seal-unit history spans multiple pumps --------------------------

def test_seal_unit_history_spans_multiple_pumps(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="RETURN_TO_STOCK", event_at="2026-02-02T00:00:00Z", created_by=_ACTOR)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-03-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_B)

    history = build_seal_unit_history(uid, **repos)
    pumps_seen = {e.payload.get("pump_tag_number") for e in history if e.event_type == TimelineCategory.SEAL_INSTALL}
    assert pumps_seen == {_PUMP_A, _PUMP_B}


# --- 15/16/17: deterministic chronology, canonical IDs, no fabricated NULLs -

def test_seal_unit_history_is_deterministically_chronological(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    create_inspection(runner, seal_unit_id=uid, inspection_date="2026-02-02T00:00:00Z", inspection_type="POST_REMOVAL", created_by=_ACTOR)

    history = build_seal_unit_history(uid, **repos)
    dates = [e.occurred_at for e in history]
    assert dates == sorted(dates)


def test_canonical_source_ids_are_preserved_in_event_ids(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    install = apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    events = build_seal_events_for_pump(_PUMP_A, **repos)
    assert events[0].id == f"SEAL_INSTALL:{install['event_id']}"


def test_null_fields_are_never_fabricated(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    create_inspection(runner, seal_unit_id=uid, inspection_date="2026-02-02T00:00:00Z", inspection_type="GENERAL", created_by=_ACTOR)  # no pump, no disposition

    # Pumpless -- correctly absent from any pump's timeline (item 9's own
    # separate proof); the seal-unit history is where a real NULL pump
    # must be preserved, not fabricated into a guessed value.
    history = build_seal_unit_history(uid, **repos)
    inspection_event = next(e for e in history if e.event_type == TimelineCategory.SEAL_INSPECTION)
    assert inspection_event.payload["pump_tag_number"] is None
    assert inspection_event.payload["disposition"] is None


# --- 25: empty seal history clean -----------------------------------------

def test_empty_seal_unit_history_for_a_fresh_unit_is_an_empty_tuple(runner, seal_unit, repos):
    assert build_seal_unit_history(seal_unit["seal_unit_id"], **repos) == ()


def test_empty_pump_history_when_no_seal_ever_touched_it(runner, repos):
    assert build_seal_events_for_pump(_PUMP_B, **repos) == ()


# --- 28: no N+1 (batched repair-by-inspection lookup) ---------------------

def test_repair_lookup_for_a_pump_is_one_batched_query_not_one_per_inspection(runner, seal_unit, repos):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    for i in range(5):
        create_inspection(runner, seal_unit_id=uid, inspection_date=f"2026-02-{i+2:02d}T00:00:00Z", inspection_type="GENERAL", created_by=_ACTOR, pump_tag_number=_PUMP_A)

    class CountingRunner:
        def __init__(self, real):
            self._real = real
            self.calls = 0

        def query_scalar(self, sql):
            self.calls += 1
            return self._real.query_scalar(sql)

    counting = CountingRunner(runner)
    counting_repos = {
        "seal_lifecycle_event_repository": SealLifecycleEventRepository(counting),
        "seal_inspection_repository": SealInspectionRepository(counting),
        "seal_repair_repository": SealRepairRepository(counting),
        "seal_warranty_assessment_repository": SealWarrantyAssessmentRepository(counting),
        "installation_report_fitment_repository": InstallationReportFitmentRepository(counting),
    }
    build_seal_events_for_pump(_PUMP_A, **counting_repos)
    # lifecycle(1) + reports(1) + inspections(1) + repairs(1, batched, not
    # one-per-inspection) + warranty(1) = 5, regardless of inspection count.
    assert counting.calls == 5
