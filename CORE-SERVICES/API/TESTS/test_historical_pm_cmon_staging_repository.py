"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- HistoricalPMCMONStagingRepository
SQL-shape tests, same FakeRunner-inspects-real-SQL discipline as
test_pm_occurrence_repository.py."""

import json
import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.historical_pm_cmon_staging_repository import (  # noqa: E402
    CMON_READING_CANDIDATE,
    EXTRACTION_PROVIDER,
    FINDING_CANDIDATE,
    PM_OCCURRENCE_CANDIDATE,
    HistoricalPMCMONStagingRepository,
    InvalidStatusTransitionError,
)


class FakeRunner:
    def __init__(self, scalar_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.scalar_response = scalar_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.scalar_response

    def execute_script(self, sql: str) -> None:
        self.scalar_calls.append(sql)


def _row(**overrides):
    base = {
        "document_field_extraction_id": "DFE-1",
        "source_document_id": "PDF-1",
        "source_document_type": "PDF",
        "detected_document_type": PM_OCCURRENCE_CANDIDATE,
        "extraction_provider": EXTRACTION_PROVIDER,
        "extracted_fields": {},
        "reviewed_fields": None,
        "status": "PENDING_REVIEW",
        "pump_tag_number": None,
        "source_page": None,
    }
    base.update(overrides)
    return base


class TestCreateCandidate:
    def test_uses_deterministic_provider_never_claude_default(self):
        runner = FakeRunner(scalar_response=json.dumps([_row()]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.create_candidate(
            source_document_id="PDF-1",
            detected_document_type=PM_OCCURRENCE_CANDIDATE,
            extracted_fields={"tag_number": "110-P-9A"},
        )

        sql = runner.scalar_calls[0]
        assert "'deterministic_workbook_table_parser'" in sql
        assert "'claude'" not in sql

    def test_starts_in_pending_review(self):
        runner = FakeRunner(scalar_response=json.dumps([_row()]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.create_candidate(
            source_document_id="PDF-1", detected_document_type=CMON_READING_CANDIDATE,
            extracted_fields={},
        )

        assert "'PENDING_REVIEW'" in runner.scalar_calls[0]

    def test_finding_candidate_type_is_a_real_distinct_value(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(detected_document_type=FINDING_CANDIDATE)]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.create_candidate(
            source_document_id="PDF-1", detected_document_type=FINDING_CANDIDATE,
            extracted_fields={"remarks": "bocor dari draingland"},
        )

        assert f"'{FINDING_CANDIDATE}'" in runner.scalar_calls[0]
        assert "cm_report" not in runner.scalar_calls[0]


class TestApplyReview:
    def test_pending_to_reviewed_is_valid(self):
        find_response = json.dumps([_row(status="PENDING_REVIEW")])
        runner = FakeRunner(scalar_response=find_response)
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.apply_review(
            "DFE-1", reviewed_fields={"tag_number": "110-P-9A"}, reviewed_by="reviewer-1",
        )

        update_sql = runner.scalar_calls[-1]
        assert "'REVIEWED'" in update_sql
        assert "reviewed_by = 'reviewer-1'" in update_sql

    def test_reviewed_fields_stored_separately_from_extracted_fields(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="PENDING_REVIEW")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.apply_review("DFE-1", reviewed_fields={"tag_number": "corrected"}, reviewed_by="r1")

        update_sql = runner.scalar_calls[-1]
        assert "reviewed_fields = " in update_sql
        assert "extracted_fields = " not in update_sql  # original extraction never overwritten

    def test_invalid_transition_raises(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="SAVED")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        with pytest.raises(InvalidStatusTransitionError):
            repo.apply_review("DFE-1", reviewed_fields={}, reviewed_by="r1", next_status="REVIEWED")

    def test_missing_candidate_returns_none(self):
        runner = FakeRunner(scalar_response="[]")
        repo = HistoricalPMCMONStagingRepository(runner)

        assert repo.apply_review("DFE-MISSING", reviewed_fields={}, reviewed_by="r1") is None


class TestReject:
    def test_reject_from_pending_review_is_valid(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="PENDING_REVIEW")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.reject("DFE-1", reviewed_by="reviewer-1")

        assert "'REJECTED'" in runner.scalar_calls[-1]

    def test_reject_from_saved_is_invalid(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="SAVED")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        with pytest.raises(InvalidStatusTransitionError):
            repo.reject("DFE-1", reviewed_by="reviewer-1")


class TestMarkSaved:
    def test_sets_saved_status(self):
        runner = FakeRunner()
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.mark_saved("DFE-1")

        assert "'SAVED'" in runner.scalar_calls[-1]


class TestListPending:
    def test_filters_by_detected_document_type_when_given(self):
        runner = FakeRunner(scalar_response="[]")
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.list_pending(detected_document_type=CMON_READING_CANDIDATE)

        sql = runner.scalar_calls[0]
        assert "status = 'PENDING_REVIEW'" in sql
        assert f"detected_document_type = '{CMON_READING_CANDIDATE}'" in sql

    def test_no_filter_lists_every_pending_type(self):
        runner = FakeRunner(scalar_response="[]")
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.list_pending()

        sql = runner.scalar_calls[0]
        assert "status = 'PENDING_REVIEW'" in sql
        assert "detected_document_type =" not in sql


class TestFindById:
    def test_returns_none_when_missing(self):
        runner = FakeRunner(scalar_response="[]")
        repo = HistoricalPMCMONStagingRepository(runner)

        assert repo.find_by_id("DFE-MISSING") is None

    def test_returns_row_when_present(self):
        runner = FakeRunner(scalar_response=json.dumps([_row()]))
        repo = HistoricalPMCMONStagingRepository(runner)

        row = repo.find_by_id("DFE-1")

        assert row["document_field_extraction_id"] == "DFE-1"


class TestListForSource:
    def test_filters_by_source_document_id(self):
        runner = FakeRunner(scalar_response="[]")
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.list_for_source("PDF-1")

        sql = runner.scalar_calls[0]
        assert "source_document_id = 'PDF-1'" in sql


class TestBulkReviewBatchAtomic:
    def test_empty_list_returns_empty_without_a_query(self):
        runner = FakeRunner()
        repo = HistoricalPMCMONStagingRepository(runner)

        assert repo.bulk_review_batch_atomic([], reviewed_by="r1") == []
        assert runner.scalar_calls == []

    def test_script_is_one_call_containing_begin_and_commit(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="REVIEWED")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.bulk_review_batch_atomic(["DFE-1", "DFE-2"], reviewed_by="reviewer-1")

        assert len(runner.scalar_calls) == 1
        sql = runner.scalar_calls[0]
        assert "BEGIN;" in sql
        assert "\nCOMMIT;\n" in sql

    def test_targets_exactly_the_given_ids(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="REVIEWED")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.bulk_review_batch_atomic(["DFE-1", "DFE-2", "DFE-3"], reviewed_by="reviewer-1")

        sql = runner.scalar_calls[0]
        assert "'DFE-1'" in sql and "'DFE-2'" in sql and "'DFE-3'" in sql

    def test_restricted_to_pending_review_and_pm_only(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="REVIEWED")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.bulk_review_batch_atomic(["DFE-1"], reviewed_by="reviewer-1")

        sql = runner.scalar_calls[0]
        assert "status = 'PENDING_REVIEW'" in sql
        assert f"detected_document_type = '{PM_OCCURRENCE_CANDIDATE}'" in sql

    def test_reviewed_fields_copied_from_extracted_fields_verbatim(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="REVIEWED")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.bulk_review_batch_atomic(["DFE-1"], reviewed_by="reviewer-1")

        sql = runner.scalar_calls[0]
        assert "reviewed_fields = extracted_fields" in sql

    def test_reviewer_is_the_given_reviewed_by(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="REVIEWED")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.bulk_review_batch_atomic(["DFE-1"], reviewed_by="reviewer-42")

        assert "reviewed_by = 'reviewer-42'" in runner.scalar_calls[0]

    def test_precheck_and_postcheck_blocks_present(self):
        runner = FakeRunner(scalar_response=json.dumps([_row(status="REVIEWED")]))
        repo = HistoricalPMCMONStagingRepository(runner)

        repo.bulk_review_batch_atomic(["DFE-1", "DFE-2"], reviewed_by="r1")

        sql = runner.scalar_calls[0]
        assert "v_eligible_count <> 2" in sql
        assert "v_reviewed_count <> 2" in sql

    def test_returns_rows_from_final_select(self):
        rows = [_row(document_field_extraction_id="DFE-1", status="REVIEWED"),
                _row(document_field_extraction_id="DFE-2", status="REVIEWED")]
        runner = FakeRunner(scalar_response=json.dumps(rows))
        repo = HistoricalPMCMONStagingRepository(runner)

        result = repo.bulk_review_batch_atomic(["DFE-1", "DFE-2"], reviewed_by="r1")

        assert [r["document_field_extraction_id"] for r in result] == ["DFE-1", "DFE-2"]


class TestFindByIdsBatched:
    def test_empty_list_returns_empty_without_a_query(self):
        runner = FakeRunner()
        assert HistoricalPMCMONStagingRepository(runner).find_by_ids([]) == []
        assert runner.scalar_calls == []

    def test_one_call_for_many_ids(self):
        runner = FakeRunner(scalar_response="[]")
        HistoricalPMCMONStagingRepository(runner).find_by_ids(["DFE-1", "DFE-2", "DFE-3"])
        assert len(runner.scalar_calls) == 1
        sql = runner.scalar_calls[0]
        assert "SELECT" in sql and "INSERT" not in sql and "UPDATE" not in sql
        assert "'DFE-1'" in sql and "'DFE-2'" in sql and "'DFE-3'" in sql

    def test_returns_parsed_rows(self):
        rows = [_row(document_field_extraction_id="DFE-1"), _row(document_field_extraction_id="DFE-2")]
        runner = FakeRunner(scalar_response=json.dumps(rows))
        result = HistoricalPMCMONStagingRepository(runner).find_by_ids(["DFE-1", "DFE-2"])
        assert [r["document_field_extraction_id"] for r in result] == ["DFE-1", "DFE-2"]
