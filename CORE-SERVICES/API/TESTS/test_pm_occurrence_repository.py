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


def test_create_draft_still_requires_a_real_schedule_for_a_real_schedule_code():
    # MWO-LTSA-HISTORICAL-PM-RECOVERY-001 regression: the live TAP
    # Engineer UI path (a real, non-"UNSCHEDULED::"-prefixed schedule
    # code) must keep requiring a genuine pm_schedule row, byte-identical
    # to before this MWO.
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type="PUMP",
        occurrence_date="2026-08-01", activities=None, remarks=None, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "EXISTS (SELECT 1 FROM pm_schedule WHERE pm_schedule_code = 'PMS-1')" in sql


def test_create_draft_skips_schedule_exists_guard_for_unscheduled_historical_placeholder():
    # The self-disclosing "UNSCHEDULED::<source>" placeholder
    # (build_unscheduled_reference, ltsa_hoc_pm_cm_upsert.py) is
    # documented to never have a matching pm_schedule row -- the EXISTS
    # guard must not block it, or historical promotion can never succeed
    # against an empty pm_schedule table (0 rows in production, not
    # hypothetical).
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="UNSCHEDULED::HOC JANUARI 2026", asset_code="211-P-18A", asset_type="PUMP",
        occurrence_date="2026-01-06", activities=None, remarks=None, created_by="actor-1",
        provenance="HISTORICAL_IMPORT", source_reference="document_field_extraction:DFE-1",
    )

    sql = runner.scalar_calls[0]
    assert "EXISTS (SELECT 1 FROM pm_schedule" not in sql
    # The pump-existence guard must still be present -- only the
    # schedule guard is conditional.
    assert "EXISTS (SELECT 1 FROM ltsa_pumps WHERE tag_number = '211-P-18A')" in sql


def test_create_draft_sets_created_by_and_updated_by_to_the_same_actor():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type=None,
        occurrence_date=None, activities=None, remarks=None, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    # MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- 4, not 2: the occurrence's
    # own created_by/updated_by, plus the atomic schedule_completion
    # UPDATE's updated_by and the schedule_audit INSERT's changed_by (the
    # same actor performs and is attributed to the whole atomic action).
    assert sql.count("'actor-1'") == 4


def test_create_draft_starts_in_draft_workflow_status():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type=None,
        occurrence_date=None, activities=None, remarks=None, created_by="actor-1",
    )

    assert "'DRAFT'" in runner.scalar_calls[0]
    assert "record_change_history" in runner.scalar_calls[0]


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
    assert "record_change_history" in sql


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


# MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- atomic schedule->actual
# completion linking: "Actual PM record is created -> Schedule becomes
# COMPLETED -> Schedule disappears from active queue", one statement, one
# transaction (never a separate round trip that could complete the
# schedule while the occurrence insert failed, or vice versa).


def test_create_draft_atomically_marks_its_owning_schedule_completed():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1", "pm_schedule_code": "PMS-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type=None,
        occurrence_date=None, activities=None, remarks=None, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert sql.strip().upper().startswith("WITH")  # single statement, single transaction
    assert "UPDATE pm_schedule SET status = 'COMPLETED'" in sql
    assert "WHERE pm_schedule_code = (SELECT pm_schedule_code FROM ins)" in sql
    assert "AND status NOT IN ('CANCELLED', 'COMPLETED')" in sql


def test_create_draft_never_completes_an_already_cancelled_or_completed_schedule():
    # The guard clause itself (status NOT IN (...)) is what actually
    # prevents this at the database level; this test only proves the
    # guard is present in every generated statement, not conditionally
    # omitted for some code path.
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type=None,
        occurrence_date="2026-09-01", activities=None, remarks=None, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "'CANCELLED', 'COMPLETED'" in sql


def test_create_draft_audits_the_schedule_completion_separately_from_the_occurrence_creation():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1"}]))
    repo = PMOccurrenceRepository(runner)

    repo.create_draft(
        pm_schedule_code="PMS-1", asset_code="211-P-18A", asset_type=None,
        occurrence_date=None, activities=None, remarks=None, created_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "'PM_OCCURRENCE', pm_occurrence_code, '__record__'" in sql
    assert "'PM_SCHEDULE', pm_schedule_code, 'status'" in sql
    assert "'AUTO_COMPLETE_ON_OCCURRENCE'" in sql


def test_soft_delete_is_audited_and_preserves_the_record():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_occurrence_code": "PMOCC-1", "deleted_by": "actor-1"}]))
    result = PMOccurrenceRepository(runner).soft_delete("PMOCC-1", deleted_by="actor-1")

    assert result["deleted_by"] == "actor-1"
    assert "deleted_at = NOW()" in runner.scalar_calls[0]
    assert "record_change_history" in runner.scalar_calls[0]
    assert "'DELETE'" in runner.scalar_calls[0]


def _promo_response(**overrides):
    base = {
        "candidate_found": True, "eligible": True, "already": None,
        "conflict": None, "inserted": {"pm_occurrence_code": "PMOCC-1"}, "marked_saved": True,
    }
    base.update(overrides)
    return json.dumps(base)


class TestPromoteHistoricalPmAtomic:
    def test_single_statement_no_explicit_begin_commit(self):
        # Postgres's own per-statement atomicity guarantee is relied on
        # (same as create_draft's own ins/schedule_completion CTE chain)
        # -- no separate BEGIN;/COMMIT; statements needed for one row.
        runner = FakeRunner(scalar_response=_promo_response())
        PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert len(runner.scalar_calls) == 1
        assert "BEGIN;" not in sql
        assert "COMMIT;" not in sql
        assert sql.strip().upper().startswith("WITH")

    def test_locks_the_candidate_row(self):
        runner = FakeRunner(scalar_response=_promo_response())
        PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert "FOR UPDATE" in runner.scalar_calls[0]

    def test_idempotency_key_is_the_existing_source_reference_column(self):
        runner = FakeRunner(scalar_response=_promo_response())
        PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert "'document_field_extraction:DFE-1'" in sql
        assert "source_reference = 'document_field_extraction:DFE-1'" in sql

    def test_requires_reviewed_pm_matched_pump_and_occurrence_date(self):
        runner = FakeRunner(scalar_response=_promo_response())
        PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert "status = 'REVIEWED'" in sql
        assert "detected_document_type = 'HISTORICAL_PM_OCCURRENCE_CANDIDATE'" in sql
        assert "pump_tag_number IS NOT NULL" in sql
        assert "fields->>'occurrence_date' IS NOT NULL" in sql

    def test_still_requires_a_real_schedule_for_a_real_schedule_code(self):
        runner = FakeRunner(scalar_response=_promo_response())
        PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="PMS-1", promoted_by="actor-1",
        )
        assert "EXISTS (SELECT 1 FROM pm_schedule WHERE pm_schedule_code = 'PMS-1')" in runner.scalar_calls[0]

    def test_skips_schedule_guard_for_unscheduled_historical_placeholder(self):
        runner = FakeRunner(scalar_response=_promo_response())
        PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert "pm_schedule WHERE pm_schedule_code" not in runner.scalar_calls[0]

    def test_insert_only_fires_when_not_already_promoted_and_not_conflicting(self):
        runner = FakeRunner(scalar_response=_promo_response())
        PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert "NOT EXISTS (SELECT 1 FROM already)" in sql
        assert "NOT EXISTS (SELECT 1 FROM conflict)" in sql

    def test_mark_saved_gated_on_the_insert_actually_happening(self):
        runner = FakeRunner(scalar_response=_promo_response())
        PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert "status = 'SAVED'" in sql
        assert "EXISTS (SELECT 1 FROM ins)" in sql

    def test_returns_parsed_result_object(self):
        runner = FakeRunner(scalar_response=_promo_response(inserted={"pm_occurrence_code": "PMOCC-42"}))
        result = PMOccurrenceRepository(runner).promote_historical_pm_atomic(
            "DFE-1", pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert result["inserted"]["pm_occurrence_code"] == "PMOCC-42"
        assert result["marked_saved"] is True


class TestPromoteHistoricalPmBatchAtomic:
    def test_empty_list_returns_empty_without_a_query(self):
        runner = FakeRunner()
        assert PMOccurrenceRepository(runner).promote_historical_pm_batch_atomic(
            [], pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        ) == []
        assert runner.scalar_calls == []

    def test_one_call_with_explicit_begin_and_commit(self):
        runner = FakeRunner(scalar_response=json.dumps([{"document_field_extraction_id": "DFE-1", "status": "SAVED", "pm_occurrence_code": "PMOCC-1"}]))
        PMOccurrenceRepository(runner).promote_historical_pm_batch_atomic(
            ["DFE-1", "DFE-2"], pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert len(runner.scalar_calls) == 1
        sql = runner.scalar_calls[0]
        assert "BEGIN;" in sql
        assert "\nCOMMIT;\n" in sql

    def test_targets_exactly_the_given_ids(self):
        runner = FakeRunner(scalar_response="[]")
        PMOccurrenceRepository(runner).promote_historical_pm_batch_atomic(
            ["DFE-1", "DFE-2", "DFE-3"], pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert "'DFE-1'" in sql and "'DFE-2'" in sql and "'DFE-3'" in sql

    def test_precheck_allows_reviewed_or_already_saved_for_retry_safety(self):
        runner = FakeRunner(scalar_response="[]")
        PMOccurrenceRepository(runner).promote_historical_pm_batch_atomic(
            ["DFE-1"], pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert "d.status IN ('REVIEWED', 'SAVED')" in sql

    def test_insert_is_idempotent_via_source_reference_not_exists_guard(self):
        runner = FakeRunner(scalar_response="[]")
        PMOccurrenceRepository(runner).promote_historical_pm_batch_atomic(
            ["DFE-1"], pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert "p2.source_reference = 'document_field_extraction:' || d.document_field_extraction_id" in sql

    def test_conflict_precheck_excludes_the_candidates_own_source_reference(self):
        runner = FakeRunner(scalar_response="[]")
        PMOccurrenceRepository(runner).promote_historical_pm_batch_atomic(
            ["DFE-1"], pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        sql = runner.scalar_calls[0]
        assert "IS DISTINCT FROM ('document_field_extraction:' || d.document_field_extraction_id)" in sql

    def test_returns_rows_from_final_select(self):
        rows = [
            {"document_field_extraction_id": "DFE-1", "status": "SAVED", "pm_occurrence_code": "PMOCC-1"},
            {"document_field_extraction_id": "DFE-2", "status": "SAVED", "pm_occurrence_code": "PMOCC-2"},
        ]
        runner = FakeRunner(scalar_response=json.dumps(rows))
        result = PMOccurrenceRepository(runner).promote_historical_pm_batch_atomic(
            ["DFE-1", "DFE-2"], pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert [r["document_field_extraction_id"] for r in result] == ["DFE-1", "DFE-2"]


def test_find_by_asset_and_date_is_a_plain_read_only_select():
    runner = FakeRunner(scalar_response="[]")
    PMOccurrenceRepository(runner).find_by_asset_and_date("211-P-18A", "2026-08-01")
    sql = runner.scalar_calls[0]
    assert "SELECT" in sql
    assert "INSERT" not in sql
    assert "UPDATE" not in sql
    assert "asset_code = '211-P-18A'" in sql
    assert "occurrence_date = '2026-08-01'" in sql
