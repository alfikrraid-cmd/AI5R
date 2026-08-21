"""MWO-LTSA-SEAL-UNIT-IDENTITY-FOUNDATION-001 -- proves migration 018
(seal_unit + installation_report.seal_unit_id/pump_tag_number) against a
REAL, disposable, published-port Postgres bootstrapped with the actual
CANONICAL_SCHEMA.sql plus every migration through 018 in order -- the
same real-schema, not-a-stub discipline test_ltsa_pumps_schema_migration.py
already established, extended here to prove the full identity-foundation
relational model (schema-level guarantees a FakeRunner-mocked unit test
cannot meaningfully prove): one seal type owning many physical units,
distinct immutable IDs, nullable serial number with known-serial
uniqueness, FK integrity on seal_code/current_pump_tag_number, and
installation_report's new nullable FKs preserving every legacy row.
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
from API.seal_unit_repository import (  # noqa: E402
    SealUnitRepository,
    SealCodeContradictionError,
    SealCodeNotFoundError,
    DuplicateSerialNumberError,
    validate_no_seal_code_contradiction,
    register_seal_unit,
)

_CONTAINER_NAME = "ai5r-test-seal-unit-migration-pg"
_USER = "ai5r"
_PASSWORD = "test-seal-unit-migration-password"
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
    )
]

_SEAL_CODE = "JC-TYPE-X"
_OTHER_SEAL_CODE = "JC-TYPE-Y"
_PUMP_TAG = "110-P-9A"


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

        # Real canonical schema, then every migration through 018, in
        # order -- exactly the sequence production bootstrap used.
        bootstrap_schema(probe, _SCHEMA_FILE)
        for migration in _MIGRATIONS:
            bootstrap_schema(probe, migration)

        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def runner(pg_port):
    """Fresh seal_unit/installation_report/ltsa_pumps/seal_registry data
    for every test -- schema stays (bootstrapped once, module-scoped),
    only rows are reset, so tests never leak state into each other."""
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script(
        "TRUNCATE seal_unit, installation_report, seal_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_PUMP_TAG}', 'HOC');"
        f"INSERT INTO seal_registry (seal_code, seal_name) VALUES ('{_SEAL_CODE}', 'Type X'), ('{_OTHER_SEAL_CODE}', 'Type Y');"
    )
    return r


def test_one_seal_type_can_own_multiple_physical_units(runner):
    repo = SealUnitRepository(runner)
    u1 = repo.create(seal_code=_SEAL_CODE)
    u2 = repo.create(seal_code=_SEAL_CODE)
    u3 = repo.create(seal_code=_SEAL_CODE)

    units = repo.list_by_seal_code(_SEAL_CODE)
    assert len(units) == 3
    assert {u1["seal_unit_id"], u2["seal_unit_id"], u3["seal_unit_id"]} == {u["seal_unit_id"] for u in units}


def test_units_have_distinct_immutable_ids(runner):
    repo = SealUnitRepository(runner)
    u1 = repo.create(seal_code=_SEAL_CODE)
    u2 = repo.create(seal_code=_SEAL_CODE)
    assert u1["seal_unit_id"] != u2["seal_unit_id"]
    # immutability: no update()/delete() method exists on the repository at all.
    assert not hasattr(repo, "update")
    assert not hasattr(repo, "delete")


def test_serial_number_is_nullable(runner):
    repo = SealUnitRepository(runner)
    unit = repo.create(seal_code=_SEAL_CODE)  # no serial_number supplied
    assert unit["serial_number"] is None
    fetched = repo.find_by_id(unit["seal_unit_id"])
    assert fetched["serial_number"] is None


def test_known_serial_uniqueness_is_enforced(runner):
    repo = SealUnitRepository(runner)
    repo.create(seal_code=_SEAL_CODE, serial_number="SN-REAL-001")
    with pytest.raises(Exception) as excinfo:
        repo.create(seal_code=_SEAL_CODE, serial_number="SN-REAL-001")
    assert "duplicate" in str(excinfo.value).lower() or "unique" in str(excinfo.value).lower()


def test_multiple_null_serials_are_allowed_never_conflated_as_duplicates(runner):
    repo = SealUnitRepository(runner)
    u1 = repo.create(seal_code=_SEAL_CODE, serial_number=None)
    u2 = repo.create(seal_code=_SEAL_CODE, serial_number=None)
    assert u1["seal_unit_id"] != u2["seal_unit_id"]


def test_seal_unit_seal_code_fk_rejects_unknown_type(runner):
    repo = SealUnitRepository(runner)
    with pytest.raises(Exception) as excinfo:
        repo.create(seal_code="NO-SUCH-TYPE")
    assert "foreign key" in str(excinfo.value).lower() or "violates" in str(excinfo.value).lower()


def test_current_pump_is_nullable(runner):
    repo = SealUnitRepository(runner)
    unit = repo.create(seal_code=_SEAL_CODE)
    assert unit["current_pump_tag_number"] is None


def test_current_pump_fk_rejects_unknown_pump(runner):
    repo = SealUnitRepository(runner)
    with pytest.raises(Exception) as excinfo:
        repo.create(seal_code=_SEAL_CODE, current_pump_tag_number="NO-SUCH-PUMP")
    assert "foreign key" in str(excinfo.value).lower() or "violates" in str(excinfo.value).lower()


def test_current_pump_fk_accepts_a_real_pump(runner):
    repo = SealUnitRepository(runner)
    unit = repo.create(seal_code=_SEAL_CODE, current_pump_tag_number=_PUMP_TAG)
    assert unit["current_pump_tag_number"] == _PUMP_TAG


def test_installation_report_seal_unit_id_is_nullable_and_fk_valid(runner):
    repo = SealUnitRepository(runner)
    unit = repo.create(seal_code=_SEAL_CODE)
    runner.execute_script(
        "INSERT INTO installation_report (installation_code, report_no, source_document_name, seal_unit_id) "
        f"VALUES ('INST-1', 'RPT-1', 'doc.pdf', '{unit['seal_unit_id']}');"
    )
    rows = _json_query("SELECT seal_unit_id FROM installation_report WHERE installation_code='INST-1'", runner)
    assert rows[0]["seal_unit_id"] == unit["seal_unit_id"]


def test_installation_report_pump_tag_number_is_nullable_and_fk_valid(runner):
    runner.execute_script(
        "INSERT INTO installation_report (installation_code, report_no, source_document_name, pump_tag_number) "
        f"VALUES ('INST-2', 'RPT-2', 'doc.pdf', '{_PUMP_TAG}');"
    )
    rows = _json_query("SELECT pump_tag_number FROM installation_report WHERE installation_code='INST-2'", runner)
    assert rows[0]["pump_tag_number"] == _PUMP_TAG


def test_legacy_installation_report_with_both_new_columns_null_remains_valid(runner):
    # Simulates a pre-existing row: neither seal_unit_id nor
    # pump_tag_number ever set -- must still insert/read cleanly.
    runner.execute_script(
        "INSERT INTO installation_report (installation_code, report_no, source_document_name, plant_equip_no, seal_code) "
        f"VALUES ('INST-LEGACY', 'RPT-LEGACY', 'legacy.pdf', '211-P-1A (legacy text)', '{_SEAL_CODE}');"
    )
    rows = _json_query(
        "SELECT installation_code, seal_unit_id, pump_tag_number, plant_equip_no, seal_code "
        "FROM installation_report WHERE installation_code='INST-LEGACY'", runner
    )
    row = rows[0]
    assert row["seal_unit_id"] is None
    assert row["pump_tag_number"] is None
    assert row["plant_equip_no"] == "211-P-1A (legacy text)"
    assert row["seal_code"] == _SEAL_CODE


def test_seal_unit_type_contradiction_is_rejected(runner):
    repo = SealUnitRepository(runner)
    unit = repo.create(seal_code=_SEAL_CODE)
    with pytest.raises(SealCodeContradictionError):
        validate_no_seal_code_contradiction(
            seal_unit_seal_code=unit["seal_code"], installation_report_seal_code=_OTHER_SEAL_CODE
        )


def test_seal_unit_type_agreement_is_accepted(runner):
    repo = SealUnitRepository(runner)
    unit = repo.create(seal_code=_SEAL_CODE)
    # must not raise
    validate_no_seal_code_contradiction(
        seal_unit_seal_code=unit["seal_code"], installation_report_seal_code=_SEAL_CODE
    )
    validate_no_seal_code_contradiction(seal_unit_seal_code=unit["seal_code"], installation_report_seal_code=None)


def test_this_migration_does_not_touch_seal_stock_quantity(runner):
    runner.execute_script(f"INSERT INTO seal_stock (seal_code, quantity_on_hand) VALUES ('{_SEAL_CODE}', 5);")
    repo = SealUnitRepository(runner)
    repo.create(seal_code=_SEAL_CODE)
    repo.create(seal_code=_SEAL_CODE)
    rows = _json_query(f"SELECT quantity_on_hand FROM seal_stock WHERE seal_code='{_SEAL_CODE}'", runner)
    assert float(rows[0]["quantity_on_hand"]) == 5.0


def test_no_warranty_column_exists_on_seal_unit(runner):
    rows = _json_query(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'seal_unit'", runner
    )
    columns = {row["column_name"] for row in rows}
    assert columns == {
        "seal_unit_id", "seal_code", "serial_number", "status",
        "current_pump_tag_number", "created_at", "updated_at",
    }


def test_no_lifecycle_event_table_was_created(runner):
    rows = _json_query(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
        "AND table_name ILIKE '%lifecycle%' OR table_name ILIKE '%seal_event%'", runner
    )
    assert rows == []


# --- MWO-LTSA-PHYSICAL-SEAL-001B -- register_seal_unit() -----------------

def test_register_seal_unit_creates_exactly_one_in_stock_unit_with_no_pump(runner):
    unit = register_seal_unit(runner, seal_code=_SEAL_CODE)
    assert unit["seal_code"] == _SEAL_CODE
    assert unit["status"] == "IN_STOCK"
    assert unit["current_pump_tag_number"] is None
    assert unit["serial_number"] is None
    rows = _json_query("SELECT count(*) AS c FROM seal_unit", runner)
    assert rows[0]["c"] == 1
    # 18: the same isolated DB's own list_all() -- the real function the
    # GET /api/ltsa/seal-units route calls -- must expose it immediately.
    listed = SealUnitRepository(runner).list_all()
    assert [u["seal_unit_id"] for u in listed] == [unit["seal_unit_id"]]


def test_register_seal_unit_rejects_unknown_seal_code(runner):
    with pytest.raises(SealCodeNotFoundError):
        register_seal_unit(runner, seal_code="NOT-A-REAL-SEAL-CODE")
    rows = _json_query("SELECT count(*) AS c FROM seal_unit", runner)
    assert rows[0]["c"] == 0


def test_register_seal_unit_persists_a_supplied_serial_number_exactly(runner):
    unit = register_seal_unit(runner, seal_code=_SEAL_CODE, serial_number="SN-0001")
    assert unit["serial_number"] == "SN-0001"


def test_register_seal_unit_rejects_a_duplicate_serial_number(runner):
    register_seal_unit(runner, seal_code=_SEAL_CODE, serial_number="SN-DUP")
    with pytest.raises(DuplicateSerialNumberError):
        register_seal_unit(runner, seal_code=_SEAL_CODE, serial_number="SN-DUP")
    rows = _json_query("SELECT count(*) AS c FROM seal_unit WHERE serial_number = 'SN-DUP'", runner)
    assert rows[0]["c"] == 1


def test_register_seal_unit_allows_multiple_null_serial_numbers(runner):
    register_seal_unit(runner, seal_code=_SEAL_CODE)
    register_seal_unit(runner, seal_code=_SEAL_CODE)
    rows = _json_query("SELECT count(*) AS c FROM seal_unit WHERE serial_number IS NULL", runner)
    assert rows[0]["c"] == 2


def test_register_seal_unit_creates_zero_side_effects(runner):
    runner.execute_script(f"INSERT INTO seal_stock (seal_code, quantity_on_hand) VALUES ('{_SEAL_CODE}', 5);")
    register_seal_unit(runner, seal_code=_SEAL_CODE)

    stock = _json_query(f"SELECT quantity_on_hand FROM seal_stock WHERE seal_code='{_SEAL_CODE}'", runner)
    assert float(stock[0]["quantity_on_hand"]) == 5.0

    compat = _json_query("SELECT count(*) AS c FROM seal_pump_compatibility", runner)
    assert compat[0]["c"] == 0

    pumps = _json_query(f"SELECT tag_number, area FROM ltsa_pumps WHERE tag_number = '{_PUMP_TAG}'", runner)
    assert pumps[0]["area"] == "HOC"
    # Lifecycle-event/inspection/repair/warranty zero-row proof lives in
    # test_seal_warranty_assessment_migration.py instead: this file only
    # bootstraps through migration 018, so those tables do not exist here
    # at all yet -- checking for their absence would prove nothing about
    # rows, only about a migration ordering this file already fixes.
