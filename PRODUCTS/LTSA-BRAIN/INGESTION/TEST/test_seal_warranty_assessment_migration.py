"""MWO-LTSA-SEAL-WARRANTY-ASSESSMENT-001 -- proves migration 021
(seal_warranty_assessment) and the calculate_warranty_window()/
create_warranty_assessment()/decide_assessment() engines against a REAL,
disposable, published-port Postgres -- the same real-schema discipline
test_seal_inspection_repair_migration.py already established.
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
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
from API.seal_unit_repository import SealUnitRepository, register_seal_unit  # noqa: E402
from API.seal_lifecycle_service import apply_lifecycle_event, SealLifecycleEventRepository  # noqa: E402
from API.seal_inspection_service import create_inspection, SealInspectionRepository  # noqa: E402
from API.seal_repair_service import SealRepairRepository  # noqa: E402
from API.seal_warranty_service import (  # noqa: E402
    calculate_warranty_window,
    create_warranty_assessment,
    decide_assessment,
    SealWarrantyAssessmentRepository,
    SealUnitNotFoundError,
    InstallationEventNotFoundError,
    NotAnInstallEventError,
    InstallationEventMismatchError,
    InspectionMismatchError,
    InvalidChronologyError,
    AssessmentNotFoundError,
    AlreadyDecidedError,
    MissingInspectionForDecisionError,
    MissingDecisionReasonError,
    InvalidDecisionError,
)

_CONTAINER_NAME = "ai5r-test-seal-warranty-pg"
_USER = "ai5r"
_PASSWORD = "test-seal-warranty-password"
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
        "TRUNCATE seal_warranty_assessment, seal_repair, seal_inspection_finding, seal_inspection, "
        "seal_lifecycle_event, seal_unit, seal_pump_compatibility, seal_stock, installation_report, "
        "seal_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_PUMP_A}', 'HOC'), ('{_PUMP_B}', 'HCC');"
        f"INSERT INTO seal_registry (seal_code, seal_name) VALUES ('{_SEAL_CODE}', 'Type X');"
    )
    return r


@pytest.fixture
def seal_unit(runner):
    return SealUnitRepository(runner).create(seal_code=_SEAL_CODE)


def _install_event(runner, seal_unit_id, *, pump=_PUMP_A, at="2026-01-01T00:00:00Z"):
    return apply_lifecycle_event(
        runner, seal_unit_id=seal_unit_id, event_type="INSTALL", event_at=at, created_by=_ACTOR, pump_tag_number=pump,
    )


def _dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# --- 1/2: installation date is INSTALL event_at, +18 calendar months -----

def test_pure_window_calculation_installation_date_plus_18_calendar_months():
    window = calculate_warranty_window(_dt("2026-01-15T00:00:00Z"), claim_date=_dt("2026-02-01T00:00:00Z"))
    assert window.installation_date == _dt("2026-01-15T00:00:00Z")
    assert window.warranty_end == _dt("2027-07-15T00:00:00Z")
    assert window.window_status == "WITHIN_WARRANTY_WINDOW"


def test_pure_window_calculation_clamps_month_end_correctly():
    # 2026-08-31 + 18 months -> 2028-02-29 (2028 is a leap year) -- real
    # calendar-month arithmetic, never fixed 547/548 days.
    window = calculate_warranty_window(_dt("2026-08-31T00:00:00Z"))
    assert window.warranty_end == _dt("2028-02-29T00:00:00Z")


# --- 3: exact end-date boundary is WITHIN -----------------------------

def test_failure_exactly_on_warranty_end_is_within_window():
    window = calculate_warranty_window(_dt("2026-01-15T00:00:00Z"), failure_date=_dt("2027-07-15T00:00:00Z"))
    assert window.window_status == "WITHIN_WARRANTY_WINDOW"


# --- 4: after end = out -------------------------------------------------

def test_failure_one_second_after_warranty_end_is_out_of_warranty():
    window = calculate_warranty_window(_dt("2026-01-15T00:00:00Z"), failure_date=_dt("2027-07-15T00:00:01Z"))
    assert window.window_status == "OUT_OF_WARRANTY"


# --- 5: before install invalid ------------------------------------------

def test_failure_before_installation_date_is_rejected_as_invalid_chronology():
    with pytest.raises(InvalidChronologyError):
        calculate_warranty_window(_dt("2026-01-15T00:00:00Z"), failure_date=_dt("2026-01-01T00:00:00Z"))


# --- 6: missing authoritative install = insufficient ---------------------

def test_no_reference_date_at_all_is_insufficient_data():
    window = calculate_warranty_window(_dt("2026-01-15T00:00:00Z"))
    assert window.window_status == "INSUFFICIENT_DATA"
    # installation_date/warranty_end are still computable -- only the
    # WINDOW classification needs a reference point.
    assert window.warranty_end == _dt("2027-07-15T00:00:00Z")


def test_create_assessment_rejects_unknown_seal_unit():
    with pytest.raises(SealUnitNotFoundError):
        create_warranty_assessment(
            None, seal_unit_id="not-a-uuid", installation_event_id="11111111-1111-4111-8111-111111111111",
            created_by=_ACTOR,
        )


# --- 15: installation event must be INSTALL -------------------------------

def test_create_assessment_rejects_a_non_install_lifecycle_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REGISTERED", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR)
    registered_event = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)[0]
    with pytest.raises(NotAnInstallEventError):
        create_warranty_assessment(
            runner, seal_unit_id=uid, installation_event_id=registered_event["event_id"], created_by=_ACTOR,
        )


# --- 16: installation event must belong to same seal ----------------------

def test_create_assessment_rejects_an_install_event_from_a_different_seal_unit(runner, seal_unit):
    other_unit = SealUnitRepository(runner).create(seal_code=_SEAL_CODE)
    other_install = _install_event(runner, other_unit["seal_unit_id"], pump=_PUMP_B)
    with pytest.raises(InstallationEventMismatchError):
        create_warranty_assessment(
            runner, seal_unit_id=seal_unit["seal_unit_id"], installation_event_id=other_install["event_id"],
            created_by=_ACTOR,
        )


def test_create_assessment_rejects_a_nonexistent_installation_event(runner, seal_unit):
    with pytest.raises(InstallationEventNotFoundError):
        create_warranty_assessment(
            runner, seal_unit_id=seal_unit["seal_unit_id"],
            installation_event_id="22222222-2222-4222-8222-222222222222", created_by=_ACTOR,
        )


# --- 7/10: within-window != accepted, pending without inspection allowed -

def test_create_assessment_defaults_to_pending_examination_never_auto_accepted(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid, at="2026-01-01T00:00:00Z")
    assessment = create_warranty_assessment(
        runner, seal_unit_id=uid, installation_event_id=install["event_id"], created_by=_ACTOR,
        failure_date="2026-06-01T00:00:00Z",
    )
    assert assessment["window_status"] == "WITHIN_WARRANTY_WINDOW"
    assert assessment["decision_status"] == "PENDING_EXAMINATION"
    assert assessment["installation_date"] is not None
    assert assessment["warranty_end"] is not None
    assert assessment["inspection_id"] is None


def test_create_assessment_out_of_warranty_still_defaults_to_pending_never_auto_rejected(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid, at="2026-01-01T00:00:00Z")
    assessment = create_warranty_assessment(
        runner, seal_unit_id=uid, installation_event_id=install["event_id"], created_by=_ACTOR,
        failure_date="2028-01-01T00:00:00Z",
    )
    assert assessment["window_status"] == "OUT_OF_WARRANTY"
    assert assessment["decision_status"] == "PENDING_EXAMINATION"


# --- 14: inspection/seal mismatch rejected --------------------------------

def test_create_assessment_rejects_an_inspection_from_a_different_seal_unit(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    other_unit = SealUnitRepository(runner).create(seal_code=_SEAL_CODE)
    other_inspection = create_inspection(
        runner, seal_unit_id=other_unit["seal_unit_id"], inspection_date="2026-02-02T00:00:00Z",
        inspection_type="GENERAL", created_by=_ACTOR,
    )
    with pytest.raises(InspectionMismatchError):
        create_warranty_assessment(
            runner, seal_unit_id=uid, installation_event_id=install["event_id"], created_by=_ACTOR,
            inspection_id=other_inspection["inspection_id"],
        )


# --- 8/9/11/12/13: decision guards ----------------------------------------

def _pending_assessment(runner, seal_unit_id, **kwargs):
    install = _install_event(runner, seal_unit_id, at=kwargs.pop("at", "2026-01-01T00:00:00Z"))
    return create_warranty_assessment(
        runner, seal_unit_id=seal_unit_id, installation_event_id=install["event_id"], created_by=_ACTOR, **kwargs
    )


def test_decision_rejects_a_non_terminal_or_unknown_decision_value(runner, seal_unit):
    assessment = _pending_assessment(runner, seal_unit["seal_unit_id"])
    for bad_decision in ("PENDING_EXAMINATION", "NOT_A_REAL_DECISION"):
        with pytest.raises(InvalidDecisionError):
            decide_assessment(
                runner, assessment_id=assessment["assessment_id"], decision=bad_decision,
                decision_reason="x", decided_by=_ACTOR,
            )


def test_decision_requires_a_reason(runner, seal_unit):
    assessment = _pending_assessment(runner, seal_unit["seal_unit_id"])
    with pytest.raises(MissingDecisionReasonError):
        decide_assessment(
            runner, assessment_id=assessment["assessment_id"], decision="NOT_APPLICABLE",
            decision_reason="", decided_by=_ACTOR,
        )


def test_not_applicable_decision_does_not_require_an_inspection(runner, seal_unit):
    assessment = _pending_assessment(runner, seal_unit["seal_unit_id"])
    decided = decide_assessment(
        runner, assessment_id=assessment["assessment_id"], decision="NOT_APPLICABLE",
        decision_reason="out of warranty window, closed without technical review", decided_by=_ACTOR,
    )
    assert decided["decision_status"] == "NOT_APPLICABLE"
    assert decided["decided_by"] == _ACTOR
    assert decided["decided_at"] is not None


def test_accept_without_any_linked_inspection_is_rejected(runner, seal_unit):
    assessment = _pending_assessment(runner, seal_unit["seal_unit_id"])
    with pytest.raises(MissingInspectionForDecisionError):
        decide_assessment(
            runner, assessment_id=assessment["assessment_id"], decision="ACCEPTED",
            decision_reason="confirmed manufacturing defect", decided_by=_ACTOR,
        )


def test_reject_without_any_linked_inspection_is_rejected(runner, seal_unit):
    assessment = _pending_assessment(runner, seal_unit["seal_unit_id"])
    with pytest.raises(MissingInspectionForDecisionError):
        decide_assessment(
            runner, assessment_id=assessment["assessment_id"], decision="REJECTED",
            decision_reason="root cause is misalignment, not covered", decided_by=_ACTOR,
        )


def test_accept_succeeds_once_a_same_seal_unit_inspection_is_linked_at_decision_time(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    assessment = _pending_assessment(runner, uid)
    # #6.3's own rule: inspection creation requires the unit NOT be
    # INSTALLED -- _pending_assessment's INSTALL leaves it INSTALLED.
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    inspection = create_inspection(
        runner, seal_unit_id=uid, inspection_date="2026-03-01T00:00:00Z", inspection_type="GENERAL",
        created_by=_ACTOR,
    )
    decided = decide_assessment(
        runner, assessment_id=assessment["assessment_id"], decision="ACCEPTED",
        decision_reason="confirmed manufacturing defect on seal face", decided_by=_ACTOR,
        inspection_id=inspection["inspection_id"],
    )
    assert decided["decision_status"] == "ACCEPTED"
    assert decided["inspection_id"] == inspection["inspection_id"]


def test_accept_rejected_when_linked_inspection_belongs_to_a_different_seal_unit(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    assessment = _pending_assessment(runner, uid)
    other_unit = SealUnitRepository(runner).create(seal_code=_SEAL_CODE)
    other_inspection = create_inspection(
        runner, seal_unit_id=other_unit["seal_unit_id"], inspection_date="2026-03-01T00:00:00Z",
        inspection_type="GENERAL", created_by=_ACTOR,
    )
    with pytest.raises(MissingInspectionForDecisionError):
        decide_assessment(
            runner, assessment_id=assessment["assessment_id"], decision="ACCEPTED",
            decision_reason="x", decided_by=_ACTOR, inspection_id=other_inspection["inspection_id"],
        )


# --- 19: finalized decision immutable -------------------------------------

def test_a_decided_assessment_cannot_be_decided_again(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    assessment = _pending_assessment(runner, uid)
    decide_assessment(
        runner, assessment_id=assessment["assessment_id"], decision="NOT_APPLICABLE",
        decision_reason="closed", decided_by=_ACTOR,
    )
    with pytest.raises(AlreadyDecidedError):
        decide_assessment(
            runner, assessment_id=assessment["assessment_id"], decision="ACCEPTED",
            decision_reason="attempted re-decision", decided_by=_ACTOR,
        )


def test_decision_never_overwrites_an_already_linked_inspection(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    inspection = create_inspection(
        runner, seal_unit_id=uid, inspection_date="2026-01-05T00:00:00Z", inspection_type="GENERAL",
        created_by=_ACTOR,
    )
    assessment = _pending_assessment(runner, uid, inspection_id=inspection["inspection_id"])
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    other_inspection = create_inspection(
        runner, seal_unit_id=uid, inspection_date="2026-01-06T00:00:00Z", inspection_type="GENERAL",
        created_by=_ACTOR,
    )
    decided = decide_assessment(
        runner, assessment_id=assessment["assessment_id"], decision="ACCEPTED", decision_reason="x",
        decided_by=_ACTOR, inspection_id=other_inspection["inspection_id"],
    )
    assert decided["inspection_id"] == inspection["inspection_id"]


# --- 17/18: reinstall creates independent warranty cycles, history preserved -

def test_reinstall_creates_a_fully_independent_second_warranty_cycle(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install_a = _install_event(runner, uid, pump=_PUMP_A, at="2026-01-01T00:00:00Z")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="RETURN_TO_STOCK", event_at="2026-02-02T00:00:00Z", created_by=_ACTOR)
    install_b = _install_event(runner, uid, pump=_PUMP_B, at="2026-03-01T00:00:00Z")

    assessment_a = create_warranty_assessment(
        runner, seal_unit_id=uid, installation_event_id=install_a["event_id"], created_by=_ACTOR,
    )
    assessment_b = create_warranty_assessment(
        runner, seal_unit_id=uid, installation_event_id=install_b["event_id"], created_by=_ACTOR,
    )

    assert assessment_a["assessment_id"] != assessment_b["assessment_id"]
    assert assessment_a["installation_date"] != assessment_b["installation_date"]
    assert _dt(assessment_a["warranty_end"]) == _dt("2027-07-01T00:00:00+00:00")
    assert _dt(assessment_b["warranty_end"]) == _dt("2027-09-01T00:00:00+00:00")

    decide_assessment(
        runner, assessment_id=assessment_a["assessment_id"], decision="NOT_APPLICABLE",
        decision_reason="cycle A closed", decided_by=_ACTOR,
    )
    # Creating/deciding cycle B's own assessment must never touch cycle A.
    all_assessments = SealWarrantyAssessmentRepository(runner).list_by_seal_unit(uid)
    assert len(all_assessments) == 2
    cycle_a_after = next(a for a in all_assessments if a["assessment_id"] == assessment_a["assessment_id"])
    assert cycle_a_after["decision_status"] == "NOT_APPLICABLE"
    cycle_b_after = next(a for a in all_assessments if a["assessment_id"] == assessment_b["assessment_id"])
    assert cycle_b_after["decision_status"] == "PENDING_EXAMINATION"


# --- 24/25/26: lifecycle/repair/stock isolation ---------------------------

def test_warranty_assessment_creation_and_decision_never_mutate_seal_unit_or_lifecycle(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    before_unit = SealUnitRepository(runner).find_by_id(uid)
    before_events = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)

    assessment = create_warranty_assessment(
        runner, seal_unit_id=uid, installation_event_id=install["event_id"], created_by=_ACTOR,
    )
    decide_assessment(
        runner, assessment_id=assessment["assessment_id"], decision="NOT_APPLICABLE",
        decision_reason="x", decided_by=_ACTOR,
    )

    after_unit = SealUnitRepository(runner).find_by_id(uid)
    after_events = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)
    assert after_unit["status"] == before_unit["status"]
    assert after_unit["current_pump_tag_number"] == before_unit["current_pump_tag_number"]
    assert after_events == before_events


def test_warranty_assessment_never_creates_a_repair_row(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    assessment = create_warranty_assessment(
        runner, seal_unit_id=uid, installation_event_id=install["event_id"], created_by=_ACTOR,
    )
    decide_assessment(
        runner, assessment_id=assessment["assessment_id"], decision="NOT_APPLICABLE",
        decision_reason="x", decided_by=_ACTOR,
    )
    assert SealRepairRepository(runner).list_by_seal_unit(uid) == []


def test_warranty_assessment_never_mutates_seal_stock(runner, seal_unit):
    from ltsa_pump_inventory_db_upsert import _json_query
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    before = _json_query("SELECT quantity_on_hand FROM seal_stock", runner)
    create_warranty_assessment(
        runner, seal_unit_id=uid, installation_event_id=install["event_id"], created_by=_ACTOR,
    )
    after = _json_query("SELECT quantity_on_hand FROM seal_stock", runner)
    assert before == after == []


# --- 27: malformed UUID clean ---------------------------------------------

def test_repository_returns_none_for_malformed_and_unknown_ids(runner):
    repo = SealWarrantyAssessmentRepository(runner)
    assert repo.find_by_id("not-a-uuid") is None
    assert repo.find_by_id("33333333-3333-4333-8333-333333333333") is None
    assert repo.list_by_seal_unit("not-a-uuid") == []


def test_create_assessment_rejects_malformed_seal_unit_id_never_a_raw_db_error(runner):
    with pytest.raises(SealUnitNotFoundError):
        create_warranty_assessment(
            runner, seal_unit_id="not-a-uuid", installation_event_id="44444444-4444-4444-8444-444444444444",
            created_by=_ACTOR,
        )


def test_decision_rejects_malformed_assessment_id_never_a_raw_db_error(runner):
    with pytest.raises(AssessmentNotFoundError):
        decide_assessment(
            runner, assessment_id="not-a-uuid", decision="NOT_APPLICABLE", decision_reason="x", decided_by=_ACTOR,
        )


# --- append-only-except-one-guarded-transition shape -----------------------

def test_repository_has_no_generic_update_or_delete_method():
    assert not hasattr(SealWarrantyAssessmentRepository, "update")
    assert not hasattr(SealWarrantyAssessmentRepository, "delete")


# --- chronological ordering -------------------------------------------------

def test_assessments_are_queryable_chronologically_by_seal_unit(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install_a = _install_event(runner, uid, pump=_PUMP_A, at="2026-03-01T00:00:00Z")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-04-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="RETURN_TO_STOCK", event_at="2026-04-02T00:00:00Z", created_by=_ACTOR)
    install_b = _install_event(runner, uid, pump=_PUMP_B, at="2026-01-01T00:00:00Z")

    create_warranty_assessment(runner, seal_unit_id=uid, installation_event_id=install_a["event_id"], created_by=_ACTOR)
    create_warranty_assessment(runner, seal_unit_id=uid, installation_event_id=install_b["event_id"], created_by=_ACTOR)

    all_assessments = SealWarrantyAssessmentRepository(runner).list_by_seal_unit(uid)
    dates = [a["installation_date"] for a in all_assessments]
    assert dates == sorted(dates)


# --- MWO-LTSA-PHYSICAL-SEAL-001B -- register_seal_unit() side-effect isolation -

def test_register_seal_unit_creates_zero_lifecycle_inspection_repair_or_warranty_rows(runner):
    # This file's own full 007-021 migration chain (unlike test_seal_unit_
    # migration.py's 018-only bootstrap) is the one place seal_lifecycle_
    # event/seal_inspection/seal_repair/seal_warranty_assessment all
    # genuinely exist, so a zero-row check here is a real proof, not a
    # vacuous one.
    register_seal_unit(runner, seal_code=_SEAL_CODE)

    from ltsa_pump_inventory_db_upsert import _json_query
    for table in ("seal_lifecycle_event", "seal_inspection", "seal_repair", "seal_warranty_assessment"):
        rows = _json_query(f"SELECT count(*) AS c FROM {table}", runner)
        assert rows[0]["c"] == 0, f"register_seal_unit() must never write to {table}"
