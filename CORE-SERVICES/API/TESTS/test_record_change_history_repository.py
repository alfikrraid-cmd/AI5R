"""MWO-LTSA-AUDIT-CHANGE-HISTORY-001 -- RecordChangeHistoryRepository
SQL-shape tests, same FakeRunner discipline as every other repository
test this session established."""

import json
import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.record_change_history_repository import RecordChangeHistoryRepository  # noqa: E402


class FakeRunner:
    def __init__(self, scalar_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.scalar_response = scalar_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.scalar_response


def test_append_never_wraps_a_bare_insert_in_a_select_from_subquery():
    runner = FakeRunner(scalar_response=json.dumps([{"change_id": "1"}]))
    repo = RecordChangeHistoryRepository(runner)

    repo.append(
        entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1", field_name="mechseal_temp_de",
        old_value="58.0", new_value="61.5", changed_by="actor-1", reason="fix",
    )

    sql = runner.scalar_calls[0]
    assert "FROM (INSERT" not in sql
    assert sql.strip().upper().startswith("WITH")
    assert "INSERT INTO record_change_history" in sql


def test_append_null_old_value_writes_real_null_not_the_string_none():
    runner = FakeRunner(scalar_response=json.dumps([{"change_id": "1"}]))
    repo = RecordChangeHistoryRepository(runner)

    repo.append(
        entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1", field_name="mechseal_temp_de",
        old_value=None, new_value="0", changed_by="actor-1", reason="fix",
    )

    sql = runner.scalar_calls[0]
    assert "'None'" not in sql
    assert "'0'" in sql


def test_list_for_entity_filters_by_entity_type_and_id():
    runner = FakeRunner(scalar_response="[]")
    repo = RecordChangeHistoryRepository(runner)

    repo.list_for_entity("INSTALLATION_REPORT", "INST-1")

    sql = runner.scalar_calls[0]
    assert "entity_type = 'INSTALLATION_REPORT'" in sql
    assert "entity_id = 'INST-1'" in sql


def test_repository_has_no_update_or_delete_method():
    assert not hasattr(RecordChangeHistoryRepository, "update")
    assert not hasattr(RecordChangeHistoryRepository, "delete")
    assert not hasattr(RecordChangeHistoryRepository, "edit")
