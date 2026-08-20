"""MWO-LTSA-SEAL-INSTALLATION-FITMENT-001 -- proves migration 022
(installation_report.installation_event_id) and
link_installation_report()'s guarded contradiction-checked linkage
against a REAL, disposable, published-port Postgres -- the same
real-schema discipline every prior seal-domain migration test file
already established.
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

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema, _json_query  # noqa: E402
from API.seal_unit_repository import SealUnitRepository  # noqa: E402
from API.seal_lifecycle_service import apply_lifecycle_event, SealLifecycleEventRepository  # noqa: E402
from API.seal_inspection_service import SealInspectionRepository  # noqa: E402
from API.seal_repair_service import SealRepairRepository  # noqa: E402
from API.seal_warranty_service import SealWarrantyAssessmentRepository, create_warranty_assessment  # noqa: E402
from API.installation_fitment_service import (  # noqa: E402
    link_installation_report,
    InstallationReportFitmentRepository,
    InstallationReportNotFoundError,
    SealUnitNotFoundError,
    InstallationEventNotFoundError,
    NotAnInstallEventError,
    SealUnitMismatchError,
    PumpMismatchError,
    SealCodeContradictionError,
    AlreadyLinkedError,
    MissingReasonError,
)

_CONTAINER_NAME = "ai5r-test-installation-fitment-pg"
_USER = "ai5r"
_PASSWORD = "test-installation-fitment-password"
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
_OTHER_SEAL_CODE = "JC-TYPE-Y"
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
        f"INSERT INTO seal_registry (seal_code, seal_name) VALUES ('{_SEAL_CODE}', 'Type X'), ('{_OTHER_SEAL_CODE}', 'Type Y');"
    )
    return r


@pytest.fixture
def seal_unit(runner):
    return SealUnitRepository(runner).create(seal_code=_SEAL_CODE)


def _install_event(runner, seal_unit_id, *, pump=_PUMP_A, at="2026-01-01T00:00:00Z"):
    return apply_lifecycle_event(
        runner, seal_unit_id=seal_unit_id, event_type="INSTALL", event_at=at, created_by=_ACTOR, pump_tag_number=pump,
    )


def _create_report(runner, *, code="INST-001", report_no="RPT-001", **overrides):
    fields = {
        "installation_code": code, "report_no": report_no, "source_document_name": "doc.pdf",
        "plant_equip_no": None, "seal_code": None, "seal_unit_id": None, "pump_tag_number": None,
    }
    fields.update(overrides)
    from ltsa_pump_inventory_db_upsert import _sql
    columns = ", ".join(fields.keys())
    values = ", ".join(_sql(v) for v in fields.values())
    runner.execute_script(f"INSERT INTO installation_report ({columns}) VALUES ({values});")
    return code


# --- 1: migration/link schema ---------------------------------------------

def test_installation_report_has_installation_event_id_column(runner):
    rows = _json_query(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'installation_report' AND column_name = 'installation_event_id'",
        runner,
    )
    assert len(rows) == 1


# --- 2: legacy report remains valid ----------------------------------------

def test_legacy_report_with_no_structured_fields_remains_valid(runner):
    code = _create_report(runner)
    report = InstallationReportFitmentRepository(runner).find_by_code(code)
    assert report["seal_unit_id"] is None
    assert report["pump_tag_number"] is None
    assert report["installation_event_id"] is None
    assert report["installation_event_at"] is None


# --- 3: link to real INSTALL succeeds ---------------------------------------

def test_link_to_a_real_install_event_succeeds(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    code = _create_report(runner)

    linked = link_installation_report(
        runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
        pump_tag_number=_PUMP_A, reason="linking legacy report to real install", linked_by=_ACTOR,
    )
    assert linked["seal_unit_id"] == uid
    assert linked["pump_tag_number"] == _PUMP_A
    assert linked["installation_event_id"] == install["event_id"]
    assert linked["linked_by"] == _ACTOR
    assert linked["link_reason"] == "linking legacy report to real install"

    fetched = InstallationReportFitmentRepository(runner).find_by_code(code)
    assert fetched["installation_event_at"] is not None


# --- 4: non-INSTALL event rejected ------------------------------------------

def test_link_rejects_a_non_install_lifecycle_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REGISTERED", event_at="2026-01-01T00:00:00Z", created_by=_ACTOR)
    registered = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)[0]
    code = _create_report(runner)
    with pytest.raises(NotAnInstallEventError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=uid, installation_event_id=registered["event_id"],
            pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR,
        )


# --- 5: seal_unit mismatch rejected -----------------------------------------

def test_link_rejects_an_install_event_belonging_to_a_different_seal_unit(runner, seal_unit):
    other_unit = SealUnitRepository(runner).create(seal_code=_SEAL_CODE)
    other_install = _install_event(runner, other_unit["seal_unit_id"], pump=_PUMP_B)
    code = _create_report(runner)
    with pytest.raises(SealUnitMismatchError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=seal_unit["seal_unit_id"],
            installation_event_id=other_install["event_id"], pump_tag_number=_PUMP_B, reason="x", linked_by=_ACTOR,
        )


# --- 6: pump mismatch rejected -----------------------------------------------

def test_link_rejects_a_pump_tag_number_that_does_not_match_the_install_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid, pump=_PUMP_A)
    code = _create_report(runner)
    with pytest.raises(PumpMismatchError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
            pump_tag_number=_PUMP_B, reason="x", linked_by=_ACTOR,
        )


# --- 7: seal_code contradiction rejected -------------------------------------

def test_link_rejects_a_seal_code_contradiction(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    code = _create_report(runner, seal_code=_OTHER_SEAL_CODE)
    with pytest.raises(SealCodeContradictionError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
            pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR,
        )


def test_link_succeeds_when_report_seal_code_already_matches(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    code = _create_report(runner, seal_code=_SEAL_CODE)
    linked = link_installation_report(
        runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
        pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR,
    )
    assert linked["seal_code"] == _SEAL_CODE


# --- 8: unknown seal_unit rejected -------------------------------------------

def test_link_rejects_an_unknown_seal_unit(runner):
    code = _create_report(runner)
    with pytest.raises(SealUnitNotFoundError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id="11111111-1111-4111-8111-111111111111",
            installation_event_id="22222222-2222-4222-8222-222222222222", pump_tag_number=_PUMP_A,
            reason="x", linked_by=_ACTOR,
        )


def test_link_rejects_malformed_seal_unit_id_never_a_raw_db_error(runner):
    code = _create_report(runner)
    with pytest.raises(SealUnitNotFoundError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id="not-a-uuid",
            installation_event_id="22222222-2222-4222-8222-222222222222", pump_tag_number=_PUMP_A,
            reason="x", linked_by=_ACTOR,
        )


# --- 9: unknown pump rejected (a made-up pump never matches a real event) --

def test_link_rejects_an_unknown_pump_because_it_can_never_match_the_real_install_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid, pump=_PUMP_A)
    code = _create_report(runner)
    with pytest.raises(PumpMismatchError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
            pump_tag_number="999-P-NOPE", reason="x", linked_by=_ACTOR,
        )


def test_link_requires_a_reason(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    code = _create_report(runner)
    with pytest.raises(MissingReasonError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
            pump_tag_number=_PUMP_A, reason="", linked_by=_ACTOR,
        )


def test_link_rejects_an_unknown_installation_report_code(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    with pytest.raises(InstallationReportNotFoundError):
        link_installation_report(
            runner, installation_code="NO-SUCH-CODE", seal_unit_id=uid, installation_event_id=install["event_id"],
            pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR,
        )


def test_link_rejects_an_unknown_installation_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    code = _create_report(runner)
    with pytest.raises(InstallationEventNotFoundError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=uid,
            installation_event_id="33333333-3333-4333-8333-333333333333", pump_tag_number=_PUMP_A,
            reason="x", linked_by=_ACTOR,
        )


# --- 10: INSTALL remains valid without report -------------------------------

def test_install_event_remains_valid_with_no_installation_report_at_all(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    assert install["event_type"] == "INSTALL"
    reports = InstallationReportFitmentRepository(runner).list_by_installation_event(install["event_id"])
    assert reports == []


# --- 11/12: creation separation ---------------------------------------------

def test_creating_a_report_never_creates_an_install_lifecycle_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    before = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)
    _create_report(runner)
    after = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)
    assert after == before


def test_install_lifecycle_event_never_creates_a_report(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    _install_event(runner, uid)
    rows = _json_query("SELECT count(*) AS c FROM installation_report", runner)
    assert rows[0]["c"] == 0


# --- 13/14: report_date != warranty anchor, warranty uses INSTALL.event_at -

def test_warranty_still_anchors_to_install_event_at_not_report_date(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid, at="2026-01-01T00:00:00Z")
    code = _create_report(runner, report_date="2026-06-01")  # a much later document date
    link_installation_report(
        runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
        pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR,
    )
    assessment = create_warranty_assessment(
        runner, seal_unit_id=uid, installation_event_id=install["event_id"], created_by=_ACTOR,
    )
    assert assessment["installation_date"].startswith("2026-01-01")
    report = InstallationReportFitmentRepository(runner).find_by_code(code)
    assert report["report_date"] == "2026-06-01"
    assert report["report_date"] != assessment["installation_date"]


# --- 15/16: reinstall preserves both histories, current_pump never rewrites R1 -

def test_reinstall_preserves_both_report_histories_independently(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install_a = _install_event(runner, uid, pump=_PUMP_A, at="2026-01-01T00:00:00Z")
    report_a = _create_report(runner, code="INST-A", report_no="RPT-A")
    link_installation_report(
        runner, installation_code=report_a, seal_unit_id=uid, installation_event_id=install_a["event_id"],
        pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR,
    )

    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-02-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="RETURN_TO_STOCK", event_at="2026-02-02T00:00:00Z", created_by=_ACTOR)
    install_b = _install_event(runner, uid, pump=_PUMP_B, at="2026-03-01T00:00:00Z")
    report_b = _create_report(runner, code="INST-B", report_no="RPT-B")
    link_installation_report(
        runner, installation_code=report_b, seal_unit_id=uid, installation_event_id=install_b["event_id"],
        pump_tag_number=_PUMP_B, reason="x", linked_by=_ACTOR,
    )

    fetched_a = InstallationReportFitmentRepository(runner).find_by_code(report_a)
    fetched_b = InstallationReportFitmentRepository(runner).find_by_code(report_b)
    assert fetched_a["installation_event_id"] == install_a["event_id"]
    assert fetched_a["pump_tag_number"] == _PUMP_A
    assert fetched_b["installation_event_id"] == install_b["event_id"]
    assert fetched_b["pump_tag_number"] == _PUMP_B

    unit = SealUnitRepository(runner).find_by_id(uid)
    assert unit["current_pump_tag_number"] == _PUMP_B
    # current_pump changing to B must never have rewritten R1's own history.
    assert fetched_a["pump_tag_number"] == _PUMP_A


# --- 22: immutable linkage / no destructive overwrite ------------------------

def test_a_linked_report_cannot_be_relinked(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    code = _create_report(runner)
    link_installation_report(
        runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
        pump_tag_number=_PUMP_A, reason="first link", linked_by=_ACTOR,
    )
    with pytest.raises(AlreadyLinkedError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
            pump_tag_number=_PUMP_A, reason="attempted relink", linked_by=_ACTOR,
        )


def test_link_rejects_a_seal_unit_that_contradicts_a_previously_set_value(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    other_unit = SealUnitRepository(runner).create(seal_code=_SEAL_CODE)
    # A report row that already carries a (hypothetically pre-populated)
    # seal_unit_id, with installation_event_id still NULL.
    code = _create_report(runner, seal_unit_id=other_unit["seal_unit_id"])
    with pytest.raises(SealUnitMismatchError):
        link_installation_report(
            runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
            pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR,
        )


# --- 23: chronological query -------------------------------------------------

def test_reports_are_queryable_chronologically_by_seal_unit_via_install_event_at(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install_a = _install_event(runner, uid, pump=_PUMP_A, at="2026-03-01T00:00:00Z")
    report_a = _create_report(runner, code="INST-LATE", report_no="RPT-LATE")
    link_installation_report(runner, installation_code=report_a, seal_unit_id=uid, installation_event_id=install_a["event_id"], pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR)

    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="REMOVE", event_at="2026-04-01T00:00:00Z", created_by=_ACTOR, pump_tag_number=_PUMP_A, reason="x")
    apply_lifecycle_event(runner, seal_unit_id=uid, event_type="RETURN_TO_STOCK", event_at="2026-04-02T00:00:00Z", created_by=_ACTOR)

    reports = InstallationReportFitmentRepository(runner).list_by_seal_unit(uid)
    dates = [r["installation_event_at"] for r in reports]
    assert dates == sorted(dates)


def test_reports_are_queryable_by_pump_and_by_installation_event(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid, pump=_PUMP_A)
    code = _create_report(runner)
    link_installation_report(runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"], pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR)

    by_pump = InstallationReportFitmentRepository(runner).list_by_pump(_PUMP_A)
    assert [r["installation_code"] for r in by_pump] == [code]

    by_event = InstallationReportFitmentRepository(runner).list_by_installation_event(install["event_id"])
    assert [r["installation_code"] for r in by_event] == [code]


# --- 24: malformed UUID clean -------------------------------------------------

def test_repository_returns_empty_for_malformed_seal_unit_or_event_id(runner):
    repo = InstallationReportFitmentRepository(runner)
    assert repo.list_by_seal_unit("not-a-uuid") == []
    assert repo.list_by_installation_event("not-a-uuid") == []


# --- 25/26/27/28: lifecycle/inspection/repair/warranty/stock isolation -------

def test_link_never_mutates_seal_unit_lifecycle_inspection_repair_warranty_or_stock(runner, seal_unit):
    uid = seal_unit["seal_unit_id"]
    install = _install_event(runner, uid)
    code = _create_report(runner)

    before_unit = SealUnitRepository(runner).find_by_id(uid)
    before_events = SealLifecycleEventRepository(runner).list_by_seal_unit(uid)
    before_inspections = SealInspectionRepository(runner).list_by_seal_unit(uid)
    before_repairs = SealRepairRepository(runner).list_by_seal_unit(uid)
    before_assessments = SealWarrantyAssessmentRepository(runner).list_by_seal_unit(uid)
    before_stock = _json_query("SELECT quantity_on_hand FROM seal_stock", runner)

    link_installation_report(
        runner, installation_code=code, seal_unit_id=uid, installation_event_id=install["event_id"],
        pump_tag_number=_PUMP_A, reason="x", linked_by=_ACTOR,
    )

    after_unit = SealUnitRepository(runner).find_by_id(uid)
    assert after_unit["status"] == before_unit["status"]
    assert after_unit["current_pump_tag_number"] == before_unit["current_pump_tag_number"]
    assert SealLifecycleEventRepository(runner).list_by_seal_unit(uid) == before_events
    assert SealInspectionRepository(runner).list_by_seal_unit(uid) == before_inspections
    assert SealRepairRepository(runner).list_by_seal_unit(uid) == before_repairs
    assert SealWarrantyAssessmentRepository(runner).list_by_seal_unit(uid) == before_assessments
    assert _json_query("SELECT quantity_on_hand FROM seal_stock", runner) == before_stock == []


# --- append-only-except-one-guarded-transition shape --------------------------

def test_repository_has_no_generic_update_or_delete_method():
    assert not hasattr(InstallationReportFitmentRepository, "update")
    assert not hasattr(InstallationReportFitmentRepository, "delete")
