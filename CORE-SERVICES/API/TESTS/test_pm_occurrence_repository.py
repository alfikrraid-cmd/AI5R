"""MWO-LTSA-PM-CM-INTAKE-001 -- PMOccurrenceRepository SQL-shape tests,
same FakeRunner-inspects-real-SQL discipline as
test_seal_master_data_repository.py."""

import json
import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.pm_occurrence_repository import PMOccurrenceRepository  # noqa: E402


class FakeRunner:
    def __init__(self, scalar_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.scalar_response = scalar_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.scalar_response


def test_create_draft_never_wraps_a_bare_insert_in_a_select_from_subquery():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type="PUMP",
        occurrence_date="2026-08-01", activities=[{"code": "1", "done": True}],
        remarks=None, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "FROM (INSERT" not in sql
    assert sql.strip().upper().startswith("WITH")
    assert "INSERT INTO pm_occurrence" in sql


def test_create_draft_sets_created_by_and_updated_by_to_the_same_actor():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type=None,
        occurrence_date=None, activities=None, remarks=None, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert sql.count("'actor-1'") == 2  # created_by and updated_by


def test_create_draft_starts_in_draft_workflow_status():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type=None,
        occurrence_date=None, activities=None, remarks=None, created_by="actor-1",
    )

    assert "'DRAFT'" in runner.scalar_calls[0]


def test_update_draft_never_references_created_by():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.update_draft(
        "PMOCC-1", occurrence_date="2026-08-02", activities=None, finding="OK",
        preliminary_recommendation="Replace seal next PM", remarks=None, updated_by="actor-2",
    )

    sql = runner.scalar_calls[0]
    assert "created_by =" not in sql
    assert "'actor-2'" in sql


def test_update_draft_only_matches_editable_workflow_states():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.update_draft(
        "PMOCC-1", occurrence_date=None, activities=None, finding=None,
        preliminary_recommendation=None, remarks=None, updated_by="actor-2",
    )

    sql = runner.scalar_calls[0]
    assert "workflow_status IN ('DRAFT', 'RETURNED_FOR_CORRECTION')" in sql


def test_update_draft_returns_none_when_no_row_matched():
    runner = FakeRunner(scalar_response="[]")
    repo = PMOccurrenceRepository(runner)

    result = repo.update_draft(
        "PMOCC-MISSING", occurrence_date=None, activities=None, finding=None,
        preliminary_recommendation=None, remarks=None, updated_by="actor-2",
    )

    assert result is None


def test_submit_sets_submitted_by_and_workflow_status():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.submit("PMOCC-1", submitted_by="actor-1")

    sql = runner.scalar_calls[0]
    assert "'SUBMITTED'" in sql
    assert "submitted_by = 'actor-1'" in sql
    assert "workflow_status IN ('DRAFT', 'RETURNED_FOR_CORRECTION')" in sql


def test_admin_return_for_correction_only_matches_submitted_state():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.admin_return_for_correction("PMOCC-1", reviewed_by="admin-1", return_reason="Missing photo evidence")

    sql = runner.scalar_calls[0]
    assert "workflow_status = 'SUBMITTED'" in sql
    assert "reviewed_by = 'admin-1'" in sql
    assert "'Missing photo evidence'" in sql
    assert "technical_reviewed_by = " not in sql  # only appears in RETURNING's column list, never assigned


def test_technical_return_for_correction_never_touches_admin_review_columns():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.technical_return_for_correction("PMOCC-1", technical_reviewed_by="jc-1", technical_comment="Recheck DE vibration")

    sql = runner.scalar_calls[0]
    assert "technical_reviewed_by = 'jc-1'" in sql
    # "reviewed_by = " only appears as a substring of "technical_reviewed_by = " --
    # the plain admin-review reviewed_by column is never separately assigned.
    assert sql.count("reviewed_by = ") == 1


def test_technical_finalize_never_touches_preliminary_recommendation():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.technical_finalize(
        "PMOCC-1", technical_reviewed_by="jc-1", technical_outcome="TECHNICALLY_APPROVED",
        technical_comment="Confirmed", technical_recommendation="Monitor next cycle",
    )

    sql = runner.scalar_calls[0]
    assert "'FINALIZED'" in sql
    assert "'TECHNICALLY_APPROVED'" in sql
    assert "technical_recommendation = 'Monitor next cycle'" in sql
    assert "preliminary_recommendation =" not in sql


def test_find_by_code_uses_a_plain_select():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    row = repo.find_by_code("PMOCC-1")

    assert row["pm_occurrence_code"] == "PMOCC-1"
    assert "FROM (SELECT" in runner.scalar_calls[0] or "FROM (" in runner.scalar_calls[0]


def test_find_by_code_returns_none_when_missing():
    runner = FakeRunner(scalar_response="[]")
    repo = PMOccurrenceRepository(runner)

    assert repo.find_by_code("PMOCC-MISSING") is None
