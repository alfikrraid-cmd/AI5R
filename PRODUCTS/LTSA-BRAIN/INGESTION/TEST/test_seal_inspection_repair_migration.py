"""MWO-LTSA-SEAL-INSPECTION-REPAIR-001 -- proves migration 020
(seal_inspection/seal_inspection_finding/seal_repair) and the
create_inspection()/create_repair() guarded-write engines against a REAL,
disposable, published-port Postgres -- the same real-schema discipline
test_seal_lifecycle_event_migration.py already established.
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
from API.seal_inspection_service import (  # noqa: E402
    create_inspection,
    SealInspectionRepository,
    SealInspectionFinding,
    SealUnitNotFoundError as InspectionSealUnitNotFoundError,
    InvalidInspectionStateError,
    UnknownPumpError,
    InvalidVocabularyError as InvalidInspectionVocabularyError,
)
from API.seal_repair_service import (  # noqa: E402
    create_repair,
    SealRepairRepository,
    SealUnitNotFoundError as RepairSealUnitNotFoundError,
    InvalidRepairStateError,
    InspectionMismatchError,
    InvalidVocabularyError as InvalidRepairVocabularyError,
)

_CONTAINER_NAME = "ai5r-test-seal-inspection-repair-pg"
_USER = "ai5r"
_PASSWORD = "test-seal-inspection-repair-password"
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
    )
]

_SEAL_CODE = "JC-TYPE-X"
_PUMP_A = "110-P-9A"
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
        "TRUNCATE seal_repair, seal_inspection_finding, seal_inspection, seal_lifecycle_event, "
        "seal_unit, seal_pump_compatibility, seal_stock, installation_report, seal_registry, "
        "ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_PUMP_A}', 'HOC');"
        f"INSERT INTO seal_registry (seal_code, seal_name) VALUES ('{_SEAL_CODE}', 'Type X');"
    )
    return r


@pytest.fixture
def in_stock_unit(runner):
    return SealUnitRepository(runner).create(seal_code=_SEAL_CODE)


@pytest.fixture
def removed_unit(runner, in_stock_unit):
    uid = in_stock_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-01-05T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="scheduled PM")
    return SealUnitRepository(runner).find_by_id(uid)


@pytest.fixture
def installed_unit(runner, in_stock_unit):
    uid = in_stock_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="INSTALL", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    return SealUnitRepository(runner).find_by_id(uid)


@pytest.fixture
def under_repair_unit(runner, removed_unit):
    uid = removed_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="SEND_FOR_REPAIR", event_at="2026-01-06T00:00:00Z", created_by=_ACTOR, reason="wear found")
    return SealUnitRepository(runner).find_by_id(uid)


def _unit_state(runner, seal_unit_id):
    return SealUnitRepository(runner).find_by_id(seal_unit_id)


def _seal_stock_qty(runner):
    from ltsa_pump_inventory_db_upsert import _json_query
    rows = _json_query("SELECT quantity_on_hand FROM seal_stock", runner)
    return [r["quantity_on_hand"] for r in rows]


# --- 1: inspection schema/FKs --------------------------------------------

def test_inspection_persists_with_expected_columns_and_fk(runner, removed_unit):
    inspection = create_inspection(
        runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
        inspection_type="POST_REMOVAL", created_by=_ACTOR, pump_tag_number=_PUMP_A,
    )
    assert inspection["seal_unit_id"] == removed_unit["seal_unit_id"]
    assert inspection["pump_tag_number"] == _PUMP_A
    assert inspection["created_by"] == _ACTOR
    assert inspection["inspection_id"]


def test_inspection_rejects_unknown_seal_unit(runner):
    with pytest.raises(InspectionSealUnitNotFoundError):
        create_inspection(
            runner, seal_unit_id="11111111-1111-4111-8111-111111111111", inspection_date="2026-01-06T00:00:00Z",
            inspection_type="GENERAL", created_by=_ACTOR,
        )


def test_inspection_rejects_malformed_seal_unit_id_never_a_raw_db_error(runner):
    with pytest.raises(InspectionSealUnitNotFoundError):
        create_inspection(
            runner, seal_unit_id="not-a-uuid", inspection_date="2026-01-06T00:00:00Z",
            inspection_type="GENERAL", created_by=_ACTOR,
        )


def test_inspection_rejects_unknown_pump(runner, removed_unit):
    with pytest.raises(UnknownPumpError):
        create_inspection(
            runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
            inspection_type="GENERAL", created_by=_ACTOR, pump_tag_number="999-P-NOPE",
        )


def test_inspection_rejects_unknown_inspection_type(runner, removed_unit):
    with pytest.raises(InvalidInspectionVocabularyError):
        create_inspection(
            runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
            inspection_type="NOT_A_REAL_TYPE", created_by=_ACTOR,
        )


def test_inspection_rejects_unknown_disposition(runner, removed_unit):
    with pytest.raises(InvalidInspectionVocabularyError):
        create_inspection(
            runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
            inspection_type="GENERAL", created_by=_ACTOR, disposition="NOT_A_REAL_DISPOSITION",
        )


def test_inspection_allows_null_disposition_when_assessment_incomplete(runner, removed_unit):
    inspection = create_inspection(
        runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
        inspection_type="GENERAL", created_by=_ACTOR, disposition=None,
    )
    assert inspection["disposition"] is None


# --- 8: invalid status rejected (inspection requires NOT INSTALLED) -----

def test_inspection_is_rejected_while_seal_unit_is_installed_even_for_general_type(runner, installed_unit):
    # Audited decision (this MWO's own conditional rule): no repository/
    # domain evidence supports in-situ inspection today, so GENERAL gets
    # no exception -- every inspection_type requires NOT INSTALLED.
    for inspection_type in ("RECEIVING", "POST_REMOVAL", "PRE_REPAIR", "POST_REPAIR", "GENERAL"):
        with pytest.raises(InvalidInspectionStateError):
            create_inspection(
                runner, seal_unit_id=installed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
                inspection_type=inspection_type, created_by=_ACTOR,
            )


def test_inspection_succeeds_once_unit_is_removed(runner, removed_unit):
    inspection = create_inspection(
        runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
        inspection_type="POST_REMOVAL", created_by=_ACTOR,
    )
    assert inspection["inspection_type"] == "POST_REMOVAL"


# --- 2/4: finding child rows, multiple findings per inspection ----------

def test_inspection_persists_multiple_finding_child_rows(runner, removed_unit):
    inspection = create_inspection(
        runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
        inspection_type="POST_REMOVAL", created_by=_ACTOR,
        findings=[
            SealInspectionFinding(component="SEAL_FACE", condition="WORN", finding="scoring visible"),
            SealInspectionFinding(component="O_RING", condition="OK"),
            SealInspectionFinding(component="SPRING", condition="OK"),
        ],
    )
    assert len(inspection["findings"]) == 3
    assert {f["component"] for f in inspection["findings"]} == {"SEAL_FACE", "O_RING", "SPRING"}

    fetched = SealInspectionRepository(runner).find_by_id(inspection["inspection_id"])
    assert len(fetched["findings"]) == 3


def test_inspection_rejects_unknown_finding_component(runner, removed_unit):
    with pytest.raises(InvalidInspectionVocabularyError):
        create_inspection(
            runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
            inspection_type="POST_REMOVAL", created_by=_ACTOR,
            findings=[SealInspectionFinding(component="NOT_A_REAL_COMPONENT")],
        )


def test_inspection_with_zero_findings_is_allowed(runner, removed_unit):
    inspection = create_inspection(
        runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
        inspection_type="GENERAL", created_by=_ACTOR,
    )
    assert inspection["findings"] == []


# --- 3: NULL vs 0 measurement --------------------------------------------

def test_finding_preserves_null_measured_value_distinct_from_zero(runner, removed_unit):
    inspection = create_inspection(
        runner, seal_unit_id=removed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
        inspection_type="POST_REMOVAL", created_by=_ACTOR,
        findings=[
            SealInspectionFinding(component="SEAL_FACE", measurement_name="face_wear_mm", measured_value=0),
            SealInspectionFinding(component="SLEEVE", measurement_name="runout_mm", measured_value=None),
        ],
    )
    by_component = {f["component"]: f["measured_value"] for f in inspection["findings"]}
    assert by_component["SEAL_FACE"] == 0
    assert by_component["SLEEVE"] is None


# --- rejected inspection writes nothing (atomicity) ----------------------

def test_rejected_inspection_persists_neither_header_nor_findings(runner, installed_unit):
    with pytest.raises(InvalidInspectionStateError):
        create_inspection(
            runner, seal_unit_id=installed_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
            inspection_type="GENERAL", created_by=_ACTOR,
            findings=[SealInspectionFinding(component="SEAL_FACE")],
        )
    assert SealInspectionRepository(runner).list_by_seal_unit(installed_unit["seal_unit_id"]) == []


# --- 5/9: repair schema/FKs, valid repair only UNDER_REPAIR --------------

def test_repair_persists_with_expected_columns_and_fk(runner, under_repair_unit):
    repair = create_repair(
        runner, seal_unit_id=under_repair_unit["seal_unit_id"], repair_date="2026-01-10T00:00:00Z",
        repair_type="OVERHAUL", repair_action="Replaced seal face and O-rings", created_by=_ACTOR,
        parts_replaced=[{"part": "seal face", "qty": 1}], repair_result="COMPLETED",
    )
    assert repair["seal_unit_id"] == under_repair_unit["seal_unit_id"]
    assert repair["repair_result"] == "COMPLETED"
    assert repair["parts_replaced"] == [{"part": "seal face", "qty": 1}]


def test_repair_rejects_unknown_seal_unit(runner):
    with pytest.raises(RepairSealUnitNotFoundError):
        create_repair(
            runner, seal_unit_id="22222222-2222-4222-8222-222222222222", repair_date="2026-01-10T00:00:00Z",
            repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR,
        )


def test_repair_is_rejected_unless_seal_unit_is_under_repair(runner, removed_unit):
    # REMOVED (not UNDER_REPAIR) -- must be rejected.
    with pytest.raises(InvalidRepairStateError):
        create_repair(
            runner, seal_unit_id=removed_unit["seal_unit_id"], repair_date="2026-01-10T00:00:00Z",
            repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR,
        )


def test_repair_rejects_unknown_repair_result(runner, under_repair_unit):
    with pytest.raises(InvalidRepairVocabularyError):
        create_repair(
            runner, seal_unit_id=under_repair_unit["seal_unit_id"], repair_date="2026-01-10T00:00:00Z",
            repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR, repair_result="NOT_A_REAL_RESULT",
        )


# --- 6: repair -> inspection seal consistency ----------------------------

def test_repair_linked_to_inspection_of_the_same_seal_unit_succeeds(runner, under_repair_unit):
    uid = under_repair_unit["seal_unit_id"]
    inspection = create_inspection(
        runner, seal_unit_id=uid, inspection_date="2026-01-06T00:00:00Z",
        inspection_type="PRE_REPAIR", created_by=_ACTOR,
    )
    repair = create_repair(
        runner, seal_unit_id=uid, inspection_id=inspection["inspection_id"], repair_date="2026-01-10T00:00:00Z",
        repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR,
    )
    assert repair["inspection_id"] == inspection["inspection_id"]


def test_repair_linked_to_inspection_of_a_different_seal_unit_is_rejected(runner, under_repair_unit):
    # A genuinely SECOND, independent seal_unit -- not the in_stock_unit
    # fixture (which under_repair_unit's own dependency chain already
    # consumed, so requesting both by name would silently alias the same
    # cached instance within one test).
    other_unit = SealUnitRepository(runner).create(seal_code=_SEAL_CODE)
    other_inspection = create_inspection(
        runner, seal_unit_id=other_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
        inspection_type="GENERAL", created_by=_ACTOR,
    )
    with pytest.raises(InspectionMismatchError):
        create_repair(
            runner, seal_unit_id=under_repair_unit["seal_unit_id"], inspection_id=other_inspection["inspection_id"],
            repair_date="2026-01-10T00:00:00Z", repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR,
        )


def test_repair_rejects_a_nonexistent_inspection_id(runner, under_repair_unit):
    with pytest.raises(InspectionMismatchError):
        create_repair(
            runner, seal_unit_id=under_repair_unit["seal_unit_id"],
            inspection_id="33333333-3333-4333-8333-333333333333",
            repair_date="2026-01-10T00:00:00Z", repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR,
        )


# --- 10: repair_result=SCRAPPED does not mutate seal_unit ----------------

def test_repair_result_scrapped_does_not_change_seal_unit_status(runner, under_repair_unit):
    uid = under_repair_unit["seal_unit_id"]
    before = _unit_state(runner, uid)
    create_repair(
        runner, seal_unit_id=uid, repair_date="2026-01-10T00:00:00Z", repair_type="OVERHAUL",
        repair_action="Beyond economical repair", created_by=_ACTOR, repair_result="SCRAPPED",
    )
    after = _unit_state(runner, uid)
    assert after["status"] == before["status"] == "UNDER_REPAIR"


# --- 11: records append-only ----------------------------------------------

def test_no_update_or_delete_method_exists_on_either_repository():
    for cls in (SealInspectionRepository, SealRepairRepository):
        assert not hasattr(cls, "update")
        assert not hasattr(cls, "delete")


# --- 18: malformed UUID clean (repair side) -------------------------------

def test_repair_rejects_malformed_seal_unit_id_never_a_raw_db_error(runner):
    with pytest.raises(RepairSealUnitNotFoundError):
        create_repair(
            runner, seal_unit_id="not-a-uuid", repair_date="2026-01-10T00:00:00Z",
            repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR,
        )


def test_inspection_repository_returns_none_for_malformed_and_unknown_id(runner):
    repo = SealInspectionRepository(runner)
    assert repo.find_by_id("not-a-uuid") is None
    assert repo.find_by_id("44444444-4444-4444-8444-444444444444") is None


def test_repair_repository_returns_none_for_malformed_and_unknown_id(runner):
    repo = SealRepairRepository(runner)
    assert repo.find_by_id("not-a-uuid") is None
    assert repo.find_by_id("44444444-4444-4444-8444-444444444444") is None


# --- 19: stock unchanged ---------------------------------------------------

def test_inspection_and_repair_creation_never_touch_seal_stock(runner, under_repair_unit):
    before = _seal_stock_qty(runner)
    inspection = create_inspection(
        runner, seal_unit_id=under_repair_unit["seal_unit_id"], inspection_date="2026-01-06T00:00:00Z",
        inspection_type="PRE_REPAIR", created_by=_ACTOR,
    )
    create_repair(
        runner, seal_unit_id=under_repair_unit["seal_unit_id"], inspection_id=inspection["inspection_id"],
        repair_date="2026-01-10T00:00:00Z", repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR,
    )
    assert _seal_stock_qty(runner) == before == []


# --- 20: lifecycle ledger unchanged by record creation --------------------

def test_inspection_and_repair_creation_never_writes_a_lifecycle_event(runner, under_repair_unit):
    uid = under_repair_unit["seal_unit_id"]
    before = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)
    inspection = create_inspection(
        runner, seal_unit_id=uid, inspection_date="2026-01-06T00:00:00Z", inspection_type="PRE_REPAIR",
        created_by=_ACTOR,
    )
    create_repair(
        runner, seal_unit_id=uid, inspection_id=inspection["inspection_id"], repair_date="2026-01-10T00:00:00Z",
        repair_type="OVERHAUL", repair_action="x", created_by=_ACTOR,
    )
    after = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)
    assert after == before


# --- 21: chronological queries ---------------------------------------------

def test_inspections_are_queryable_chronologically_by_seal_unit_and_by_pump(runner, removed_unit):
    uid = removed_unit["seal_unit_id"]
    create_inspection(runner, seal_unit_id=uid, inspection_date="2026-01-10T00:00:00Z", inspection_type="GENERAL", created_by=_ACTOR, pump_tag_number=_PUMP_A)
    create_inspection(runner, seal_unit_id=uid, inspection_date="2026-01-05T00:00:00Z", inspection_type="POST_REMOVAL", created_by=_ACTOR, pump_tag_number=_PUMP_A)

    by_unit = SealInspectionRepository(runner).list_by_seal_unit(uid)
    assert [i["inspection_date"] for i in by_unit] == sorted(i["inspection_date"] for i in by_unit)

    by_pump = SealInspectionRepository(runner).list_by_pump(_PUMP_A)
    assert [i["inspection_date"] for i in by_pump] == sorted(i["inspection_date"] for i in by_pump)
    assert len(by_pump) == 2


def test_repairs_are_queryable_chronologically_by_seal_unit(runner, under_repair_unit):
    uid = under_repair_unit["seal_unit_id"]
    create_repair(runner, seal_unit_id=uid, repair_date="2026-01-12T00:00:00Z", repair_type="A", repair_action="x", created_by=_ACTOR, repair_result="PARTIAL")
    create_repair(runner, seal_unit_id=uid, repair_date="2026-01-10T00:00:00Z", repair_type="B", repair_action="y", created_by=_ACTOR, repair_result="COMPLETED")

    by_unit = SealRepairRepository(runner).list_by_seal_unit(uid)
    assert [r["repair_date"] for r in by_unit] == sorted(r["repair_date"] for r in by_unit)
