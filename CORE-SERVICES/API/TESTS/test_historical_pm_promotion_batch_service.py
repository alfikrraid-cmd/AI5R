"""MWO-LTSA-ATOMIC-PM-PROMOTION-001 -- pure-logic tests for
historical_pm_promotion_batch_service.py, same Protocol-based Fake
repository discipline as test_historical_selective_staging_service.py /
test_historical_bulk_review_service.py."""

import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.historical_pm_promotion_batch_service import (  # noqa: E402
    MAX_PROMOTION_BATCH,
    BatchTooLargeError,
    DuplicateCandidateIdError,
    EmptyBatchError,
    PromotionBatchError,
    promote_pm_batch,
    validate_promotion_batch,
)


def _candidate(candidate_id, **overrides):
    base = {
        "document_field_extraction_id": candidate_id,
        "detected_document_type": "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
        "status": "REVIEWED",
        "pump_tag_number": "110-P-9A",
        "extracted_fields": {"occurrence_date": "2026-07-01"},
        "reviewed_fields": None,
    }
    base.update(overrides)
    return base


class FakeStagingRepo:
    def __init__(self, candidates):
        self._candidates = {c["document_field_extraction_id"]: c for c in candidates}

    def find_by_id(self, candidate_id):
        c = self._candidates.get(candidate_id)
        return dict(c) if c else None


class FakePMOccurrenceRepo:
    def __init__(self, *, by_source_reference=None, by_asset_date=None):
        self._by_source_reference = by_source_reference or {}
        self._by_asset_date = by_asset_date or {}
        self.batch_calls: list[dict] = []
        self.raise_on_atomic = None

    def find_by_source_reference(self, source_reference):
        row = self._by_source_reference.get(source_reference)
        return dict(row) if row else None

    def find_by_asset_and_date(self, asset_code, occurrence_date):
        row = self._by_asset_date.get((asset_code, occurrence_date))
        return dict(row) if row else None

    def promote_historical_pm_batch_atomic(self, candidate_ids, *, pm_schedule_code, promoted_by):
        self.batch_calls.append({
            "candidate_ids": list(candidate_ids), "pm_schedule_code": pm_schedule_code, "promoted_by": promoted_by,
        })
        if self.raise_on_atomic:
            raise self.raise_on_atomic
        return [
            {"document_field_extraction_id": cid, "status": "SAVED", "pm_occurrence_code": f"PMOCC-{cid}"}
            for cid in candidate_ids
        ]


class TestValidatePromotionBatch:
    def test_empty_raises(self):
        with pytest.raises(EmptyBatchError):
            validate_promotion_batch(FakeStagingRepo([]), FakePMOccurrenceRepo(), [])

    def test_over_limit_raises(self):
        ids = [f"DFE-{i}" for i in range(MAX_PROMOTION_BATCH + 1)]
        with pytest.raises(BatchTooLargeError):
            validate_promotion_batch(FakeStagingRepo([]), FakePMOccurrenceRepo(), ids)

    def test_duplicate_ids_raise(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        with pytest.raises(DuplicateCandidateIdError):
            validate_promotion_batch(staging, FakePMOccurrenceRepo(), ["DFE-1", "DFE-1"])

    def test_all_valid(self):
        staging = FakeStagingRepo([_candidate("DFE-1"), _candidate("DFE-2")])
        result = validate_promotion_batch(staging, FakePMOccurrenceRepo(), ["DFE-1", "DFE-2"])
        assert result["all_valid"] is True
        assert result["counts"] == {"VALID": 2}

    def test_missing_candidate_is_not_found(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        result = validate_promotion_batch(staging, FakePMOccurrenceRepo(), ["DFE-1", "DFE-MISSING"])
        assert result["all_valid"] is False
        assert result["counts"]["NOT_FOUND"] == 1

    def test_wrong_domain_excluded(self):
        staging = FakeStagingRepo([_candidate("DFE-1", detected_document_type="HISTORICAL_CMON_READING_CANDIDATE")])
        result = validate_promotion_batch(staging, FakePMOccurrenceRepo(), ["DFE-1"])
        assert result["counts"]["WRONG_DOMAIN"] == 1

    def test_pending_review_excluded(self):
        staging = FakeStagingRepo([_candidate("DFE-1", status="PENDING_REVIEW")])
        result = validate_promotion_batch(staging, FakePMOccurrenceRepo(), ["DFE-1"])
        assert result["counts"]["WRONG_STATUS"] == 1

    def test_unresolved_pump_excluded(self):
        staging = FakeStagingRepo([_candidate("DFE-1", pump_tag_number=None)])
        result = validate_promotion_batch(staging, FakePMOccurrenceRepo(), ["DFE-1"])
        assert result["counts"]["UNKNOWN_PUMP"] == 1

    def test_missing_occurrence_date_excluded(self):
        staging = FakeStagingRepo([_candidate("DFE-1", extracted_fields={})])
        result = validate_promotion_batch(staging, FakePMOccurrenceRepo(), ["DFE-1"])
        assert result["counts"]["INVALID_FIELDS"] == 1

    def test_already_promoted_is_valid_for_retry(self):
        staging = FakeStagingRepo([_candidate("DFE-1", status="SAVED")])
        pm_repo = FakePMOccurrenceRepo(by_source_reference={
            "document_field_extraction:DFE-1": {"pm_occurrence_code": "PMOCC-1"},
        })
        result = validate_promotion_batch(staging, pm_repo, ["DFE-1"])
        assert result["all_valid"] is True
        assert result["counts"] == {"ALREADY_PROMOTED": 1}

    def test_conflict_with_different_candidates_final_pm_blocks_batch(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo(by_asset_date={
            ("110-P-9A", "2026-07-01"): {"pm_occurrence_code": "PMOCC-OTHER", "source_reference": "document_field_extraction:DFE-OTHER"},
        })
        result = validate_promotion_batch(staging, pm_repo, ["DFE-1"])
        assert result["all_valid"] is False
        assert result["counts"]["CONFLICT"] == 1

    def test_same_source_reference_is_not_a_conflict(self):
        # find_by_asset_and_date returning THIS candidate's own row (a
        # prior promotion of itself) must not be misread as a conflict --
        # already caught earlier by find_by_source_reference.
        staging = FakeStagingRepo([_candidate("DFE-1", status="SAVED")])
        pm_repo = FakePMOccurrenceRepo(
            by_source_reference={"document_field_extraction:DFE-1": {"pm_occurrence_code": "PMOCC-1"}},
            by_asset_date={("110-P-9A", "2026-07-01"): {"pm_occurrence_code": "PMOCC-1", "source_reference": "document_field_extraction:DFE-1"}},
        )
        result = validate_promotion_batch(staging, pm_repo, ["DFE-1"])
        assert result["counts"] == {"ALREADY_PROMOTED": 1}


class TestPromotePmBatch:
    def test_all_valid_promotes_all_and_reports_promoted(self):
        staging = FakeStagingRepo([_candidate("DFE-1"), _candidate("DFE-2")])
        pm_repo = FakePMOccurrenceRepo()
        result = promote_pm_batch(
            staging, pm_repo, ["DFE-1", "DFE-2"],
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert result["status"] == "PROMOTED"
        assert len(result["results"]) == 2
        assert pm_repo.batch_calls[0]["candidate_ids"] == ["DFE-1", "DFE-2"]
        assert pm_repo.batch_calls[0]["promoted_by"] == "actor-1"

    def test_any_ineligible_promotes_nothing(self):
        staging = FakeStagingRepo([_candidate("DFE-1"), _candidate("DFE-2", status="PENDING_REVIEW")])
        pm_repo = FakePMOccurrenceRepo()
        result = promote_pm_batch(
            staging, pm_repo, ["DFE-1", "DFE-2"],
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert result["status"] == "REJECTED_PRECHECK_FAILED"
        assert result["results"] == []
        assert pm_repo.batch_calls == []

    def test_atomic_transaction_failure_is_reported_not_raised(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo()
        pm_repo.raise_on_atomic = RuntimeError("db exploded")
        result = promote_pm_batch(
            staging, pm_repo, ["DFE-1"],
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert result["status"] == "REJECTED_ATOMIC_TRANSACTION_FAILED"
        assert result["results"] == []
        assert "db exploded" in result["error"]

    def test_exact_retry_after_full_success_is_a_safe_no_op(self):
        staging = FakeStagingRepo([_candidate("DFE-1", status="SAVED")])
        pm_repo = FakePMOccurrenceRepo(by_source_reference={
            "document_field_extraction:DFE-1": {"pm_occurrence_code": "PMOCC-1"},
        })
        result = promote_pm_batch(
            staging, pm_repo, ["DFE-1"],
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
        )
        assert result["status"] == "PROMOTED"
        assert result["precheck"]["counts"] == {"ALREADY_PROMOTED": 1}

    def test_malformed_request_still_raises(self):
        with pytest.raises(EmptyBatchError):
            promote_pm_batch(
                FakeStagingRepo([]), FakePMOccurrenceRepo(), [],
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
            )

    def test_atomic_row_count_mismatch_raises(self):
        class ShortRepo(FakePMOccurrenceRepo):
            def promote_historical_pm_batch_atomic(self, candidate_ids, *, pm_schedule_code, promoted_by):
                return []

        staging = FakeStagingRepo([_candidate("DFE-1")])
        with pytest.raises(PromotionBatchError):
            promote_pm_batch(
                staging, ShortRepo(), ["DFE-1"],
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="actor-1",
            )
