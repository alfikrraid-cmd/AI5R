"""MWO-LTSA-BULK-HISTORICAL-REVIEW-001 -- pure-logic tests for
historical_bulk_review_service.py, same Protocol-based Fake repository
discipline as test_historical_selective_staging_service.py."""

import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.historical_bulk_review_service import (  # noqa: E402
    MAX_BULK_REVIEW_BATCH,
    BatchTooLargeError,
    DuplicateCandidateIdError,
    EmptyBatchError,
    bulk_review_candidates,
    validate_bulk_review_batch,
)


def _candidate(candidate_id, **overrides):
    base = {
        "document_field_extraction_id": candidate_id,
        "detected_document_type": "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
        "status": "PENDING_REVIEW",
    }
    base.update(overrides)
    return base


class FakeRepo:
    def __init__(self, candidates):
        self._candidates = {c["document_field_extraction_id"]: c for c in candidates}
        self.bulk_review_calls = []
        self.raise_on_atomic = None

    def find_by_id(self, candidate_id):
        c = self._candidates.get(candidate_id)
        return dict(c) if c else None

    def bulk_review_batch_atomic(self, candidate_ids, *, reviewed_by):
        self.bulk_review_calls.append({"candidate_ids": list(candidate_ids), "reviewed_by": reviewed_by})
        if self.raise_on_atomic:
            raise self.raise_on_atomic
        return [
            {**self._candidates[cid], "status": "REVIEWED", "reviewed_by": reviewed_by}
            for cid in candidate_ids
        ]


class TestValidateBulkReviewBatch:
    def test_empty_raises(self):
        with pytest.raises(EmptyBatchError):
            validate_bulk_review_batch(FakeRepo([]), [])

    def test_over_limit_raises(self):
        ids = [f"DFE-{i}" for i in range(MAX_BULK_REVIEW_BATCH + 1)]
        with pytest.raises(BatchTooLargeError):
            validate_bulk_review_batch(FakeRepo([]), ids)

    def test_duplicate_ids_raise(self):
        repo = FakeRepo([_candidate("DFE-1")])
        with pytest.raises(DuplicateCandidateIdError):
            validate_bulk_review_batch(repo, ["DFE-1", "DFE-1"])

    def test_all_valid(self):
        repo = FakeRepo([_candidate("DFE-1"), _candidate("DFE-2")])
        result = validate_bulk_review_batch(repo, ["DFE-1", "DFE-2"])
        assert result["all_valid"] is True
        assert result["counts"] == {"VALID": 2}

    def test_missing_candidate_is_not_found(self):
        repo = FakeRepo([_candidate("DFE-1")])
        result = validate_bulk_review_batch(repo, ["DFE-1", "DFE-MISSING"])
        assert result["all_valid"] is False
        assert result["counts"]["NOT_FOUND"] == 1

    def test_wrong_status_excluded(self):
        repo = FakeRepo([_candidate("DFE-1", status="REVIEWED")])
        result = validate_bulk_review_batch(repo, ["DFE-1"])
        assert result["all_valid"] is False
        assert result["counts"]["WRONG_STATUS"] == 1

    def test_wrong_domain_excluded(self):
        repo = FakeRepo([_candidate("DFE-1", detected_document_type="HISTORICAL_CMON_READING_CANDIDATE")])
        result = validate_bulk_review_batch(repo, ["DFE-1"])
        assert result["all_valid"] is False
        assert result["counts"]["WRONG_DOMAIN"] == 1


class TestBulkReviewCandidates:
    def test_all_valid_stages_all_and_reports_reviewed(self):
        repo = FakeRepo([_candidate("DFE-1"), _candidate("DFE-2")])
        result = bulk_review_candidates(repo, ["DFE-1", "DFE-2"], reviewed_by="actor-1")
        assert result["status"] == "REVIEWED"
        assert len(result["reviewed"]) == 2
        assert repo.bulk_review_calls[0]["reviewed_by"] == "actor-1"
        assert repo.bulk_review_calls[0]["candidate_ids"] == ["DFE-1", "DFE-2"]

    def test_any_invalid_reviews_nothing(self):
        repo = FakeRepo([_candidate("DFE-1"), _candidate("DFE-2", status="REVIEWED")])
        result = bulk_review_candidates(repo, ["DFE-1", "DFE-2"], reviewed_by="actor-1")
        assert result["status"] == "REJECTED_PRECHECK_FAILED"
        assert result["reviewed"] == []
        assert repo.bulk_review_calls == []

    def test_atomic_transaction_failure_is_reported_not_raised(self):
        repo = FakeRepo([_candidate("DFE-1")])
        repo.raise_on_atomic = RuntimeError("db exploded")
        result = bulk_review_candidates(repo, ["DFE-1"], reviewed_by="actor-1")
        assert result["status"] == "REJECTED_ATOMIC_TRANSACTION_FAILED"
        assert result["reviewed"] == []
        assert "db exploded" in result["error"]

    def test_malformed_request_still_raises(self):
        with pytest.raises(EmptyBatchError):
            bulk_review_candidates(FakeRepo([]), [], reviewed_by="actor-1")
