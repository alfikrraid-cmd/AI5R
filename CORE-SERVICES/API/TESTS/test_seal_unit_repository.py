"""MWO-LTSA-SEAL-UNIT-IDENTITY-FOUNDATION-001 -- SealUnitRepository
SQL-shape tests, same FakeRunner discipline as every other repository
test this session established (see test_record_change_history_repository.py)."""

import json
import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

import pytest  # noqa: E402

from API.seal_unit_repository import (  # noqa: E402
    SealUnitRepository,
    SealUnitError,
    SEAL_UNIT_STATUSES,
)


class FakeRunner:
    def __init__(self, scalar_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.scalar_response = scalar_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.scalar_response


def test_create_never_wraps_a_bare_insert_in_a_select_from_subquery():
    runner = FakeRunner(scalar_response=json.dumps([{"seal_unit_id": "u1"}]))
    repo = SealUnitRepository(runner)

    repo.create(seal_code="JC-TYPE-X")

    sql = runner.scalar_calls[0]
    assert "FROM (INSERT" not in sql
    assert sql.strip().upper().startswith("WITH")
    assert "INSERT INTO seal_unit" in sql


def test_create_rejects_an_unknown_status_before_ever_touching_the_runner():
    runner = FakeRunner()
    repo = SealUnitRepository(runner)

    with pytest.raises(SealUnitError):
        repo.create(seal_code="JC-TYPE-X", status="NOT_A_REAL_STATUS")

    assert runner.scalar_calls == []


def test_create_defaults_to_in_stock():
    runner = FakeRunner(scalar_response=json.dumps([{"seal_unit_id": "u1"}]))
    repo = SealUnitRepository(runner)

    repo.create(seal_code="JC-TYPE-X")

    assert "'IN_STOCK'" in runner.scalar_calls[0]


def test_all_seven_identity_safe_statuses_are_accepted():
    for status in SEAL_UNIT_STATUSES:
        runner = FakeRunner(scalar_response=json.dumps([{"seal_unit_id": "u1"}]))
        repo = SealUnitRepository(runner)
        repo.create(seal_code="JC-TYPE-X", status=status)  # must not raise


def test_seal_unit_statuses_is_exactly_the_seven_mwo_defined_states():
    assert SEAL_UNIT_STATUSES == {
        "IN_STOCK", "INSTALLED", "REMOVED", "UNDER_INSPECTION", "UNDER_REPAIR", "REPAIRED", "SCRAPPED",
    }


def test_find_by_id_filters_by_seal_unit_id():
    # MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001's malformed-UUID closure
    # made find_by_id() short-circuit (never touch the runner) for any
    # non-UUID id -- a real UUID-shaped id is required here to exercise
    # the SQL-shape this test actually cares about. The short-circuit
    # itself is proven separately in test_is_valid_uuid_* below.
    runner = FakeRunner(scalar_response="[]")
    repo = SealUnitRepository(runner)

    repo.find_by_id("11111111-1111-4111-8111-111111111111")

    sql = runner.scalar_calls[0]
    assert "seal_unit_id = '11111111-1111-4111-8111-111111111111'" in sql


def test_find_by_id_never_touches_the_runner_for_a_malformed_id():
    runner = FakeRunner(scalar_response="[]")
    repo = SealUnitRepository(runner)

    result = repo.find_by_id("unit-123")

    assert result is None
    assert runner.scalar_calls == []


def test_list_by_seal_code_filters_by_type():
    runner = FakeRunner(scalar_response="[]")
    repo = SealUnitRepository(runner)

    repo.list_by_seal_code("JC-TYPE-X")

    sql = runner.scalar_calls[0]
    assert "seal_code = 'JC-TYPE-X'" in sql


def test_no_update_or_delete_method_exists():
    # Identity-foundation scope only: no status-transition/removal method
    # anywhere on this repository yet.
    assert not hasattr(SealUnitRepository, "update")
    assert not hasattr(SealUnitRepository, "delete")
    assert not hasattr(SealUnitRepository, "update_status")
    assert not hasattr(SealUnitRepository, "install")
    assert not hasattr(SealUnitRepository, "remove")
    assert not hasattr(SealUnitRepository, "repair")
