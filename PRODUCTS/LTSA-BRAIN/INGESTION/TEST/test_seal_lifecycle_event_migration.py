"""MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001 -- proves migration 019
(seal_lifecycle_event) and apply_lifecycle_event()'s transition engine
against a REAL, disposable, published-port Postgres bootstrapped with
the actual CANONICAL_SCHEMA.sql plus every migration through 019, in
order -- the same real-schema discipline test_seal_unit_migration.py
already established. Proves the relational/transactional guarantees a
FakeRunner-mocked test cannot: atomicity, row-level concurrency locking,
and the full physical-seal lifecycle sequence.
"""

from __future__ import annotations

import subprocess
import sys
import threading
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

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema, _json_query  # noqa: E402
from API.seal_unit_repository import SealUnitRepository  # noqa: E402
from API.seal_lifecycle_service import (  # noqa: E402
    apply_lifecycle_event,
    SealLifecycleEventRepository,
    SealUnitNotFoundError,
    InvalidLifecycleTransitionError,
    MissingReasonError,
    IncompatiblePumpError,
)

_CONTAINER_NAME = "ai5r-test-seal-lifecycle-event-pg"
_USER = "ai5r"
_PASSWORD = "test-seal-lifecycle-event-password"
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
        "TRUNCATE seal_lifecycle_event, seal_unit, seal_pump_compatibility, seal_stock, "
        "installation_report, seal_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_PUMP_A}', 'HOC'), ('{_PUMP_B}', 'HCC');"
        f"INSERT INTO seal_registry (seal_code, seal_name) VALUES ('{_SEAL_CODE}', 'Type X');"
    )
    return r


@pytest.fixture
def seal_unit(runner):
    repo = SealUnitRepository(runner)
    return repo.create(seal_code=_SEAL_CODE)


def _events(runner, seal_unit_id):
    return SealLifecycleEventRepository(runner).list_by_seal_unit(seal_unit_id)


def _unit_state(runner, seal_unit_id):
    return SealUnitRepository(runner).find_by_id(seal_unit_id)


# --- 1: append-only -----------------------------------------------------

def test_no_update_or_delete_repository_method_or_route_exists():
    assert not hasattr(SealLifecycleEventRepository, "update")
    assert not hasattr(SealLifecycleEventRepository, "delete")
    assert not hasattr(SealLifecycleEventRepository, "update_event")


# --- 2/9: every event type, full sequence -------------------------------

def test_full_lifecycle_sequence_register_install_a_remove_inspect_repair_return_install_b(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REGISTERED", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-02T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="scheduled PM")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="SEND_FOR_INSPECTION", event_at="2026-02-02T00:00:00Z", created_by=_ACTOR, reason="routine check")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSPECTION_COMPLETED", event_at="2026-02-03T00:00:00Z", created_by=_ACTOR)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="SEND_FOR_REPAIR", event_at="2026-02-04T00:00:00Z", created_by=_ACTOR, reason="wear found")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REPAIR_COMPLETED", event_at="2026-02-10T00:00:00Z", created_by=_ACTOR)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="RETURN_TO_STOCK", event_at="2026-02-11T00:00:00Z", created_by=_ACTOR)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-03-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_B)

    events = _events(runner, uid)
    assert [e["event_type"] for e in events] == [
        "REGISTERED", "INSTALL", "REMOVE", "SEND_FOR_INSPECTION", "INSPECTION_COMPLETED",
        "SEND_FOR_REPAIR", "REPAIR_COMPLETED", "RETURN_TO_STOCK", "INSTALL",
    ]
    # 10: complete historical events remain -- both INSTALL rows (A and B) still present.
    installs = [e for e in events if e["event_type"] == "INSTALL"]
    assert [e["pump_tag_number"] for e in installs] == [_PUMP_A, _PUMP_B]

    # 11: current state ends at B only.
    unit = _unit_state(runner, uid)
    assert unit["status"] == "INSTALLED"
    assert unit["current_pump_tag_number"] == _PUMP_B


# --- 3/4: valid vs invalid transitions -----------------------------------

def test_install_from_fresh_in_stock_unit_is_valid(runner, seal_unit):
    event = apply_lifecycle_event(
        runner, seal_unit_id=seal_unit["seal_unit_id"], event_type="INSTALL",
        event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A,
    )
    assert event["event_type"] == "INSTALL"


def test_install_while_already_installed_is_rejected(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    with pytest.raises(InvalidLifecycleTransitionError):
        apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-02T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_B)


def test_remove_without_prior_install_is_rejected(runner, seal_unit):
    with pytest.raises(InvalidLifecycleTransitionError):
        apply_lifecycle_event(
            runner, seal_unit_id=seal_unit["seal_unit_id"], event_type="REMOVE",
            event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x",
        )


# --- 5: INSTALL requires pump --------------------------------------------

def test_install_without_pump_tag_number_is_rejected(runner, seal_unit):
    with pytest.raises(Exception):
        apply_lifecycle_event(
            runner, seal_unit_id=seal_unit["seal_unit_id"], event_type="INSTALL",
            event_at="2026-01-01T00:00:00Z", created_by=_ACTOR,
        )


# --- 6: REMOVE pump consistency ------------------------------------------

def test_remove_with_a_different_pump_than_currently_installed_is_rejected(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    with pytest.raises(InvalidLifecycleTransitionError):
        apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-01-02T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_B, reason="x")
    # current state unaffected by the rejected attempt
    assert _unit_state(runner, uid)["current_pump_tag_number"] == _PUMP_A


# --- 7: SCRAPPED terminal -------------------------------------------------

def test_scrapped_unit_cannot_receive_any_further_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="SCRAP", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, reason="corroded beyond repair")
    assert _unit_state(runner, uid)["status"] == "SCRAPPED"
    for event_type, kwargs in (
        ("INSTALL", {"pump_tag_number": _PUMP_A}),
        ("SEND_FOR_INSPECTION", {"reason": "x"}),
        ("SEND_FOR_REPAIR", {"reason": "x"}),
        ("RETURN_TO_STOCK", {}),
        ("SCRAP", {"reason": "x"}),
    ):
        with pytest.raises(InvalidLifecycleTransitionError):
            apply_lifecycle_event(runner, seal_unit_id=uid, event_type=event_type, event_at="2026-01-02T00:00:00Z", created_by=_ACTOR, **kwargs)


# --- 8: reinstall same seal on another pump after REMOVE -----------------

def test_reinstall_same_seal_on_a_different_pump_after_remove(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-01-02T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="RETURN_TO_STOCK", event_at="2026-01-03T00:00:00Z", created_by=_ACTOR)
    event = apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-04T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_B)
    assert event["pump_tag_number"] == _PUMP_B
    assert _unit_state(runner, uid)["current_pump_tag_number"] == _PUMP_B


# --- 12: atomic event+state rollback --------------------------------------

def test_rejected_transition_writes_neither_event_nor_state_change(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    before_events = len(_events(runner, uid))
    before_state = _unit_state(runner, uid)
    with pytest.raises(InvalidLifecycleTransitionError):
        apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    assert len(_events(runner, uid)) == before_events
    assert _unit_state(runner, uid) == before_state


# --- 13: concurrent double-install prevented ------------------------------

def test_concurrent_install_attempts_never_leave_a_unit_on_two_pumps(pg_port, seal_unit):
    uid = seal_unit["seal_unit_id"]
    outcomes = []

    def _attempt(pump_tag):
        r = DatabaseRunner(DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE))
        try:
            apply_lifecycle_event(r, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=pump_tag)
            outcomes.append(("success", pump_tag))
        except InvalidLifecycleTransitionError:
            outcomes.append(("rejected", pump_tag))

    t1 = threading.Thread(target=_attempt, args=(_PUMP_A,))
    t2 = threading.Thread(target=_attempt, args=(_PUMP_B,))
    t1.start(); t2.start()
    t1.join(); t2.join()

    successes = [o for o in outcomes if o[0] == "success"]
    assert len(successes) == 1, f"expected exactly one successful INSTALL, got {outcomes}"

    verify_runner = DatabaseRunner(DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE))
    final = SealUnitRepository(verify_runner).find_by_id(uid)
    assert final["current_pump_tag_number"] == successes[0][1]
    install_events = [e for e in SealLifecycleEventRepository(verify_runner).list_by_seal_unit(uid) if e["event_type"] == "INSTALL"]
    assert len(install_events) == 1


# --- 15: required reasons -------------------------------------------------

@pytest.mark.parametrize("event_type,kwargs", [
    ("REMOVE", {"pump_tag_number": _PUMP_A}),
    ("SEND_FOR_INSPECTION", {}),
    ("SEND_FOR_REPAIR", {}),
    ("SCRAP", {}),
])
def test_reason_required_event_types_reject_a_missing_reason(runner, seal_unit, event_type, kwargs):
    uid = seal_unit["seal_unit_id"]
    if event_type in ("REMOVE",):
        apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    with pytest.raises(MissingReasonError):
        apply_lifecycle_event(runner, seal_unit_id=uid, event_type=event_type, event_at="2026-01-02T00:00:00Z", created_by=_ACTOR, **kwargs)


@pytest.mark.parametrize("event_type", ["REGISTERED", "INSPECTION_COMPLETED", "REPAIR_COMPLETED", "RETURN_TO_STOCK"])
def test_reason_optional_event_types_succeed_without_a_reason(runner, seal_unit, event_type):
    uid = seal_unit["seal_unit_id"]
    if event_type in ("INSPECTION_COMPLETED",):
        apply_lifecycle_event(runner, seal_unit_id=uid, event_type="SEND_FOR_INSPECTION", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, reason="x")
    if event_type in ("REPAIR_COMPLETED",):
        apply_lifecycle_event(runner, seal_unit_id=uid, event_type="SEND_FOR_REPAIR", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, reason="x")
    event = apply_lifecycle_event(runner, seal_unit_id=uid, event_type=event_type, event_at="2026-01-02T00:00:00Z", created_by=_ACTOR)
    assert event["reason"] is None


# --- 16: pump FK -----------------------------------------------------------

def test_install_against_a_nonexistent_pump_is_rejected(runner, seal_unit):
    with pytest.raises(Exception):
        apply_lifecycle_event(
            runner, seal_unit_id=seal_unit["seal_unit_id"], event_type="INSTALL",
            event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number="NO-SUCH-PUMP",
        )
    # nothing persisted from the FK-violating attempt
    assert _events(runner, seal_unit["seal_unit_id"]) == []


# --- 17: compatibility behavior ---------------------------------------------

def test_install_succeeds_when_no_compatibility_rows_exist_for_this_seal_type(runner, seal_unit):
    # Production-empty seal_pump_compatibility must never silently block
    # every future INSTALL (this MWO's own explicit instruction).
    rows = _json_query(f"SELECT COUNT(*) AS n FROM seal_pump_compatibility WHERE seal_code = '{_SEAL_CODE}'", runner)
    assert rows[0]["n"] == 0
    event = apply_lifecycle_event(
        runner, seal_unit_id=seal_unit["seal_unit_id"], event_type="INSTALL",
        event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A,
    )
    assert event["event_type"] == "INSTALL"


def test_install_rejects_an_incompatible_pump_when_compatibility_rows_exist(runner, seal_unit):
    runner.execute_script(f"INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number) VALUES ('{_SEAL_CODE}', '{_PUMP_A}');")
    with pytest.raises(IncompatiblePumpError):
        apply_lifecycle_event(
            runner, seal_unit_id=seal_unit["seal_unit_id"], event_type="INSTALL",
            event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_B,
        )


def test_install_accepts_a_compatible_pump_when_compatibility_rows_exist(runner, seal_unit):
    runner.execute_script(f"INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number) VALUES ('{_SEAL_CODE}', '{_PUMP_A}');")
    event = apply_lifecycle_event(
        runner, seal_unit_id=seal_unit["seal_unit_id"], event_type="INSTALL",
        event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A,
    )
    assert event["event_type"] == "INSTALL"


# --- unknown seal_unit ------------------------------------------------------

def test_unknown_seal_unit_id_raises_not_found(runner):
    with pytest.raises(SealUnitNotFoundError):
        apply_lifecycle_event(
            runner, seal_unit_id="00000000-0000-0000-0000-000000000000", event_type="REGISTERED",
            event_at="2026-01-01T00:00:00Z", created_by=_ACTOR,
        )


def test_malformed_seal_unit_id_raises_not_found_never_a_raw_db_error(runner):
    with pytest.raises(SealUnitNotFoundError):
        apply_lifecycle_event(
            runner, seal_unit_id="not-a-uuid-at-all", event_type="REGISTERED",
            event_at="2026-01-01T00:00:00Z", created_by=_ACTOR,
        )


# --- 21: stock unchanged -----------------------------------------------------

def test_lifecycle_events_never_change_seal_stock_quantity(runner, seal_unit):
    runner.execute_script(f"INSERT INTO seal_stock (seal_code, quantity_on_hand) VALUES ('{_SEAL_CODE}', 12);")
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-01-02T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    rows = _json_query(f"SELECT quantity_on_hand FROM seal_stock WHERE seal_code = '{_SEAL_CODE}'", runner)
    assert float(rows[0]["quantity_on_hand"]) == 12.0


# --- registered is first-event-only, never re-registerable ------------------

def test_registered_can_only_be_the_first_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REGISTERED", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR)
    with pytest.raises(InvalidLifecycleTransitionError):
        apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REGISTERED", event_at="2026-01-02T00:00:00Z", created_by=_ACTOR)


def test_registered_does_not_change_current_state(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    before = _unit_state(runner, uid)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REGISTERED", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR)
    after = _unit_state(runner, uid)
    assert before["status"] == after["status"]
    assert before["current_pump_tag_number"] == after["current_pump_tag_number"]


# --- chronological query readiness (#6.6) ------------------------------------

def test_events_are_orderable_chronologically_by_seal_unit(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REGISTERED", event_at="2026-01-05T00:00:00Z", created_by=_ACTOR)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    events = _events(runner, uid)
    assert [e["event_at"] for e in events] == sorted(e["event_at"] for e in events)


def test_events_are_queryable_chronologically_by_pump(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-01-02T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    events = SealLifecycleEventRepository(runner).list_by_pump(_PUMP_A)
    assert [e["event_type"] for e in events] == ["INSTALL", "REMOVE"]
