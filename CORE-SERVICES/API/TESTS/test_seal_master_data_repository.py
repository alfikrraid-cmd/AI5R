"""MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- seal_master_data_repository
coverage, same FakeRunner-inspects-real-SQL-shape discipline as
test_auth_repository.py (a duck-typed fake never catches an invalid CTE
shape; only inspecting the actual SQL string does -- Task 5-equivalent
real-Postgres proof lives in the disposable-Postgres verification run
separately, not in this file).
"""

import json
import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.seal_master_data_repository import (  # noqa: E402
    SealMasterDataRepository,
    normalize_identifier_field,
)


class FakeRunner:
    def __init__(self, scalar_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.scalar_response = scalar_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.scalar_response


# --- normalize_identifier_field (Phase 17: explicit empty-string/NULL) ----


def test_normalize_identifier_field_none_stays_none():
    assert normalize_identifier_field(None) is None


def test_normalize_identifier_field_empty_string_becomes_none():
    assert normalize_identifier_field("") is None


def test_normalize_identifier_field_whitespace_only_becomes_none():
    assert normalize_identifier_field("   ") is None


def test_normalize_identifier_field_real_value_is_stripped_and_kept():
    assert normalize_identifier_field("  KIMAP-0001  ") == "KIMAP-0001"


# --- find_seal_identifiers -------------------------------------------------


def test_find_seal_identifiers_uses_a_plain_select_via_json_query():
    runner = FakeRunner(scalar_response=json.dumps([{"seal_code": "SC-001", "kimap_pertamina": None}]))
    repo = SealMasterDataRepository(runner)

    row = repo.find_seal_identifiers("SC-001")

    assert row["seal_code"] == "SC-001"
    assert "FROM (SELECT" in runner.scalar_calls[0] or "FROM (" in runner.scalar_calls[0]


def test_find_seal_identifiers_returns_none_when_seal_does_not_exist():
    runner = FakeRunner(scalar_response="[]")
    repo = SealMasterDataRepository(runner)

    assert repo.find_seal_identifiers("SC-MISSING") is None


# --- update_seal_identifiers ------------------------------------------------


def test_update_seal_identifiers_never_wraps_a_bare_update_in_a_select_from_subquery():
    # The exact bug class auth_repository.create_user already hit once:
    # `SELECT ... FROM (UPDATE ...) t` is invalid PostgreSQL syntax.
    runner = FakeRunner(scalar_response=json.dumps([{"seal_code": "SC-001"}]))
    repo = SealMasterDataRepository(runner)

    repo.update_seal_identifiers(
        "SC-001", kimap_pertamina="KIMAP-0001", gpn_john_crane=None, updated_by="actor-1"
    )

    sql = runner.scalar_calls[0]
    assert "FROM (UPDATE" not in sql
    assert sql.strip().upper().startswith("WITH")
    assert "UPDATE seal_registry" in sql
    assert "RETURNING" in sql


def test_update_seal_identifiers_sets_both_fields_and_updated_by():
    runner = FakeRunner(scalar_response=json.dumps([{"seal_code": "SC-001"}]))
    repo = SealMasterDataRepository(runner)

    repo.update_seal_identifiers(
        "SC-001", kimap_pertamina="KIMAP-0001", gpn_john_crane="GPN-JC-9001", updated_by="actor-1"
    )

    sql = runner.scalar_calls[0]
    assert "'KIMAP-0001'" in sql
    assert "'GPN-JC-9001'" in sql
    assert "'actor-1'" in sql
    assert "updated_at = NOW()" in sql


def test_update_seal_identifiers_never_references_created_by_or_seal_stock():
    # Hard Rule 10/11 (creator never overwritten) and Phase 10 (stock
    # quantity is not reachable through this API) are both structural
    # facts about this SQL, not runtime checks -- proven by their literal
    # absence from the statement this function builds.
    runner = FakeRunner(scalar_response=json.dumps([{"seal_code": "SC-001"}]))
    repo = SealMasterDataRepository(runner)

    repo.update_seal_identifiers(
        "SC-001", kimap_pertamina="KIMAP-0001", gpn_john_crane=None, updated_by="actor-1"
    )

    sql = runner.scalar_calls[0]
    assert "created_by =" not in sql
    assert "seal_stock" not in sql
    assert "quantity_on_hand" not in sql


def test_update_seal_identifiers_never_touches_ingestion_owned_columns():
    runner = FakeRunner(scalar_response=json.dumps([{"seal_code": "SC-001"}]))
    repo = SealMasterDataRepository(runner)

    repo.update_seal_identifiers(
        "SC-001", kimap_pertamina="KIMAP-0001", gpn_john_crane=None, updated_by="actor-1"
    )

    sql = runner.scalar_calls[0]
    for column in ("seal_name =", "manufacturer =", "model =", "shaft_size =", "status ="):
        assert column not in sql


def test_update_seal_identifiers_returns_none_when_seal_does_not_exist():
    runner = FakeRunner(scalar_response="[]")
    repo = SealMasterDataRepository(runner)

    result = repo.update_seal_identifiers(
        "SC-MISSING", kimap_pertamina="KIMAP-0001", gpn_john_crane=None, updated_by="actor-1"
    )

    assert result is None


def test_update_seal_identifiers_can_clear_a_field_back_to_null():
    runner = FakeRunner(scalar_response=json.dumps([{"seal_code": "SC-001", "kimap_pertamina": None}]))
    repo = SealMasterDataRepository(runner)

    repo.update_seal_identifiers(
        "SC-001", kimap_pertamina=None, gpn_john_crane=None, updated_by="actor-1"
    )

    sql = runner.scalar_calls[0]
    assert "kimap_pertamina = NULL" in sql
