"""MWO-LTSA-PM-CM-INTAKE-001 -- ConditionMonitoringReadingRepository
SQL-shape tests, same FakeRunner discipline as
test_pm_occurrence_repository.py (the sibling domain, identical
workflow shape)."""

import json
import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.condition_monitoring_reading_repository import ConditionMonitoringReadingRepository  # noqa: E402


class FakeRunner:
    def __init__(self, scalar_response: str = "[]", scalar_responses: list[str] | None = None):
        self.scalar_calls: list[str] = []
        self.scalar_response = scalar_response
        self.scalar_responses = list(scalar_responses or [])

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        if self.scalar_responses:
            return self.scalar_responses.pop(0)
        return self.scalar_response


_SAMPLE_MEASUREMENTS = {
    "suction_temp": 34.0, "discharge_temp": 37.2, "mechseal_temp_de": 50.1,
    "mechanical_seal_leak_de": False, "vertical_vibration_de": 1.5,
}


def test_create_draft_never_wraps_a_bare_insert_in_a_select_from_subquery():
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_reading_code": "CMONR-1"}]))
    repo = ConditionMonitoringReadingRepository(runner)

    repo.create_draft(
        condition_monitoring_schedule_code="CMS-1", asset_code="G-201-01A", asset_type="PUMP",
        reading_date="2026-08-01", measurements=_SAMPLE_MEASUREMENTS, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "FROM (INSERT" not in sql
    assert sql.strip().upper().startswith("WITH")
    assert "INSERT INTO condition_monitoring_reading" in sql
    assert "'DRAFT'" in sql


def test_create_draft_writes_real_measurement_values():
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_reading_code": "CMONR-1"}]))
    repo = ConditionMonitoringReadingRepository(runner)

    repo.create_draft(
        condition_monitoring_schedule_code="CMS-1", asset_code="G-201-01A", asset_type=None,
        reading_date=None, measurements=_SAMPLE_MEASUREMENTS, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "34.0" in sql
    assert "FALSE" in sql  # mechanical_seal_leak_de


def test_create_draft_missing_measurement_is_null_never_zero():
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_reading_code": "CMONR-1"}]))
    repo = ConditionMonitoringReadingRepository(runner)

    repo.create_draft(
        condition_monitoring_schedule_code="CMS-1", asset_code="G-201-01A", asset_type=None,
        reading_date=None, measurements={}, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    # every measurement column with no supplied value renders as a literal
    # NULL, never a fabricated 0 -- Hard Rule 11.
    assert "NULL" in sql
    assert ", 0," not in sql
    assert "record_change_history" in sql


def test_update_draft_only_matches_editable_workflow_states():
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_reading_code": "CMONR-1"}]))
    repo = ConditionMonitoringReadingRepository(runner)

    repo.update_draft(
        "CMONR-1", reading_date="2026-08-02", measurements=_SAMPLE_MEASUREMENTS,
        finding="Elevated vibration on DE side", updated_by="actor-2",
    )

    sql = runner.scalar_calls[0]
    assert "workflow_status IN ('DRAFT', 'RETURNED_FOR_CORRECTION')" in sql
    assert "created_by =" not in sql


def test_submit_sets_submitted_by_and_workflow_status():
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_reading_code": "CMONR-1"}]))
    repo = ConditionMonitoringReadingRepository(runner)

    repo.submit("CMONR-1", submitted_by="actor-1")

    sql = runner.scalar_calls[0]
    assert "'SUBMITTED'" in sql
    assert "submitted_by = 'actor-1'" in sql


def test_technical_finalize_sets_finalized_and_outcome():
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_reading_code": "CMONR-1"}]))
    repo = ConditionMonitoringReadingRepository(runner)

    repo.technical_finalize(
        "CMONR-1", technical_reviewed_by="jc-1", technical_outcome="ACKNOWLEDGED",
        technical_comment="Within normal range", technical_recommendation=None,
    )

    sql = runner.scalar_calls[0]
    assert "'FINALIZED'" in sql
    assert "'ACKNOWLEDGED'" in sql
    assert "workflow_status = 'SUBMITTED'" in sql  # only a submitted record can be finalized


def test_find_by_code_returns_none_when_missing():
    runner = FakeRunner(scalar_response="[]")
    repo = ConditionMonitoringReadingRepository(runner)

    assert repo.find_by_code("CMONR-MISSING") is None


def test_list_all_returns_bounded_page_and_total_metadata():
    runner = FakeRunner(scalar_responses=[
        json.dumps([{"condition_monitoring_reading_code": "CMONR-1"}]),
        json.dumps([{"total": 51}]),
    ])
    repo = ConditionMonitoringReadingRepository(runner)

    result = repo.list_all(limit=25, offset=50)

    assert result["items"] == [{"condition_monitoring_reading_code": "CMONR-1"}]
    assert result["total"] == 51
    assert result["limit"] == 25
    assert result["offset"] == 50
    assert "LIMIT 25 OFFSET 50" in runner.scalar_calls[0]
    assert "COUNT(*) AS total" in runner.scalar_calls[1]


def test_soft_delete_is_audited_and_preserves_the_record():
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_reading_code": "CMONR-1", "deleted_by": "actor-1"}]))
    result = ConditionMonitoringReadingRepository(runner).soft_delete("CMONR-1", deleted_by="actor-1")

    assert result["deleted_by"] == "actor-1"
    assert "deleted_at = NOW()" in runner.scalar_calls[0]
    assert "record_change_history" in runner.scalar_calls[0]
    assert "'DELETE'" in runner.scalar_calls[0]
