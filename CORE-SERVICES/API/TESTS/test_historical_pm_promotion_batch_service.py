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
        self.find_by_ids_calls: list[list] = []

    def find_by_id(self, candidate_id):
        c = self._candidates.get(candidate_id)
        return dict(c) if c else None

    def find_by_ids(self, candidate_ids):
        self.find_by_ids_calls.append(list(candidate_ids))
        return [dict(self._candidates[cid]) for cid in candidate_ids if cid in self._candidates]


class FakePMOccurrenceRepo:
    def __init__(self, *, by_source_reference=None, by_asset_date=None):
        self._by_source_reference = by_source_reference or {}
        self._by_asset_date = by_asset_date or {}
        self.batch_calls: list[dict] = []
        self.raise_on_atomic = None
        self.find_by_source_references_calls: list[list] = []
        self.find_by_asset_dates_calls: list[list] = []

    def find_by_source_reference(self, source_reference):
        row = self._by_source_reference.get(source_reference)
        return dict(row) if row else None

    def find_by_source_references(self, source_references):
        self.find_by_source_references_calls.append(list(source_references))
        return [
            {"source_reference": s, **self._by_source_reference[s]}
            for s in source_references if s in self._by_source_reference
        ]

    def find_by_asset_and_date(self, asset_code, occurrence_date):
        row = self._by_asset_date.get((asset_code, occurrence_date))
        return dict(row) if row else None

    def find_by_asset_dates(self, pairs):
        self.find_by_asset_dates_calls.append(list(pairs))
        seen = set()
        rows = []
        for pair in pairs:
            if pair in self._by_asset_date and pair not in seen:
                seen.add(pair)
                asset_code, occurrence_date = pair
                # the real repository's SELECT always includes these
                # columns; the fake's fixture dicts only carry the
                # fields each test actually cares about, so fill them
                # in from the lookup key itself.
                rows.append({"asset_code": asset_code, "occurrence_date": occurrence_date, **self._by_asset_date[pair]})
        return rows

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

    def test_mixed_reviewed_and_saved_in_same_batch_is_all_valid(self):
        # a partially-promoted retry batch -- some rows already SAVED
        # (from a prior successful run), some newly REVIEWED -- must
        # validate as a whole, not just the REVIEWED subset.
        staging = FakeStagingRepo([
            _candidate("DFE-1", status="SAVED"),
            _candidate("DFE-2", status="REVIEWED", extracted_fields={"occurrence_date": "2026-07-02"}),
        ])
        pm_repo = FakePMOccurrenceRepo(by_source_reference={
            "document_field_extraction:DFE-1": {"pm_occurrence_code": "PMOCC-1"},
        })
        result = validate_promotion_batch(staging, pm_repo, ["DFE-1", "DFE-2"])
        assert result["all_valid"] is True
        assert result["counts"] == {"ALREADY_PROMOTED": 1, "VALID": 1}

    def test_540_scale_all_valid_uses_a_bounded_query_count_not_3n(self):
        # MWO-LTSA-RECOVERY-STATUS-LATENCY-001 -- the actual performance
        # regression proof: N=540 must NOT cost ~3*540 repository calls
        # (the old per-candidate pattern measured at ~1,624 real DB
        # round trips / ~54s in production). Exactly one batched call per
        # repository method, regardless of N.
        candidates = [
            _candidate(f"DFE-{i}", extracted_fields={"occurrence_date": f"2026-01-{(i % 27) + 1:02d}"})
            for i in range(540)
        ]
        staging = FakeStagingRepo(candidates)
        pm_repo = FakePMOccurrenceRepo()
        ids = [c["document_field_extraction_id"] for c in candidates]

        result = validate_promotion_batch(staging, pm_repo, ids)

        assert result["all_valid"] is True
        assert result["counts"] == {"VALID": 540}
        assert len(staging.find_by_ids_calls) == 1
        assert len(staging.find_by_ids_calls[0]) == 540
        assert len(pm_repo.find_by_source_references_calls) == 1
        assert len(pm_repo.find_by_source_references_calls[0]) == 540
        assert len(pm_repo.find_by_asset_dates_calls) == 1
        assert len(pm_repo.find_by_asset_dates_calls[0]) == 540
        # exactly 3 repository round trips total for the whole batch,
        # never one per candidate.
        total_calls = (
            len(staging.find_by_ids_calls)
            + len(pm_repo.find_by_source_references_calls)
            + len(pm_repo.find_by_asset_dates_calls)
        )
        assert total_calls == 3

    def test_response_contract_unchanged_shape_and_keys(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        result = validate_promotion_batch(staging, FakePMOccurrenceRepo(), ["DFE-1"])
        assert set(result.keys()) == {"results", "counts", "all_valid"}
        assert set(result["results"][0].keys()) >= {"candidate_id", "status"}
        assert isinstance(result["counts"], dict)
        assert isinstance(result["all_valid"], bool)


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
