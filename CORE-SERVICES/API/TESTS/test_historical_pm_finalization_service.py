"""MWO-LTSA-HISTORICAL-PM-FINALIZATION-001 -- pure-logic tests for
historical_pm_finalization_service.py, same Protocol-based Fake
repository discipline as test_historical_pm_promotion_batch_service.py."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.historical_pm_finalization_service import (  # noqa: E402
    FinalizationBatchError,
    fetch_finalization_targets,
    finalization_readiness,
    finalize_historical_pm_batch,
    validate_finalization_batch,
)


def _candidate(candidate_id, **overrides):
    base = {
        "document_field_extraction_id": candidate_id,
        "detected_document_type": "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
        "status": "SAVED",
        "extracted_fields": {"occurrence_date": "2026-07-01", "candidate_identity_v2": f"HASH-{candidate_id}"},
        "reviewed_by": "reviewer-1",
        "reviewed_at": "2026-07-15T00:00:00",
    }
    base.update(overrides)
    return base


def _pm_row(candidate_id, **overrides):
    base = {
        "pm_occurrence_code": f"PMOCC-{candidate_id}",
        "source_reference": f"document_field_extraction:{candidate_id}",
        "asset_code": "110-P-9A",
        "occurrence_date": "2026-07-01",
        "workflow_status": "DRAFT",
    }
    base.update(overrides)
    return base


class FakeStagingRepo:
    def __init__(self, candidates):
        self._candidates = list(candidates)
        self.list_by_status_calls: list[tuple] = []

    def list_by_status(self, status, detected_document_type=None):
        self.list_by_status_calls.append((status, detected_document_type))
        return [
            dict(c) for c in self._candidates
            if c["status"] == status
            and (detected_document_type is None or c["detected_document_type"] == detected_document_type)
        ]


class FakePMOccurrenceRepo:
    def __init__(self, pm_rows, *, valid_pump_tags=None):
        self._pm_rows = list(pm_rows)
        self._valid_pump_tags = valid_pump_tags if valid_pump_tags is not None else {"110-P-9A"}
        self.find_by_source_references_calls: list[list] = []
        self.find_by_asset_dates_calls: list[list] = []
        self.find_valid_pump_tags_calls: list[list] = []
        self.finalize_calls: list[dict] = []
        self.raise_on_atomic = None

    def find_by_source_references(self, source_references):
        self.find_by_source_references_calls.append(list(source_references))
        wanted = set(source_references)
        return [dict(r) for r in self._pm_rows if r["source_reference"] in wanted]

    def find_by_asset_dates(self, pairs):
        self.find_by_asset_dates_calls.append(list(pairs))
        wanted = set(pairs)
        return [dict(r) for r in self._pm_rows if (r["asset_code"], r["occurrence_date"]) in wanted]

    def find_valid_pump_tags(self, tags):
        self.find_valid_pump_tags_calls.append(list(tags))
        return {t for t in tags if t in self._valid_pump_tags}

    def finalize_historical_batch_atomic(self, pm_occurrence_codes, *, finalized_by):
        self.finalize_calls.append({"pm_occurrence_codes": list(pm_occurrence_codes), "finalized_by": finalized_by})
        if self.raise_on_atomic:
            raise self.raise_on_atomic
        return [
            {**next(r for r in self._pm_rows if r["pm_occurrence_code"] == code), "workflow_status": "FINALIZED"}
            for code in pm_occurrence_codes
        ]


class TestFetchFinalizationTargets:
    def test_wrong_domain_excluded(self):
        staging = FakeStagingRepo([_candidate("DFE-1", detected_document_type="HISTORICAL_CMON_READING_CANDIDATE")])
        assert fetch_finalization_targets(staging) == []

    def test_missing_identity_excluded(self):
        staging = FakeStagingRepo([_candidate("DFE-1", extracted_fields={"occurrence_date": "2026-07-01"})])
        assert fetch_finalization_targets(staging) == []

    def test_non_saved_status_never_fetched(self):
        # list_by_status is called with SAVED only -- a REVIEWED/
        # PENDING_REVIEW recovery member is never a finalization target.
        staging = FakeStagingRepo([_candidate("DFE-1", status="REVIEWED")])
        assert fetch_finalization_targets(staging) == []
        assert staging.list_by_status_calls == [("SAVED", "HISTORICAL_PM_OCCURRENCE_CANDIDATE")]

    def test_matched_recovery_candidate_included(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        targets = fetch_finalization_targets(staging)
        assert [t["document_field_extraction_id"] for t in targets] == ["DFE-1"]


class TestValidateFinalizationBatch:
    def test_1_exact_valid_recovery_population_is_ready(self):
        staging = FakeStagingRepo([_candidate("DFE-1"), _candidate("DFE-2", extracted_fields={"occurrence_date": "2026-07-02", "candidate_identity_v2": "HASH-DFE-2"})])
        pm_repo = FakePMOccurrenceRepo([
            _pm_row("DFE-1"),
            _pm_row("DFE-2", occurrence_date="2026-07-02"),
        ])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is True
        assert result["counts"] == {"ELIGIBLE": 2}
        assert set(result["eligible_pm_occurrence_codes"]) == {"PMOCC-DFE-1", "PMOCC-DFE-2"}

    def test_2_saved_candidate_required(self):
        staging = FakeStagingRepo([_candidate("DFE-1", status="REVIEWED")])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")])
        result = validate_finalization_batch(staging, pm_repo)
        # REVIEWED is never even a target (fetch_finalization_targets
        # only fetches SAVED) -- an empty, vacuously-ready batch.
        assert result["results"] == []
        assert result["all_eligible"] is True

    def test_3_candidate_identity_v2_required(self):
        staging = FakeStagingRepo([_candidate("DFE-1", extracted_fields={"occurrence_date": "2026-07-01"})])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["results"] == []  # never a target at all

    def test_4_review_metadata_required_reviewed_by(self):
        staging = FakeStagingRepo([_candidate("DFE-1", reviewed_by=None)])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is False
        assert result["counts"]["MISSING_REVIEWED_BY"] == 1

    def test_4_review_metadata_required_reviewed_at(self):
        staging = FakeStagingRepo([_candidate("DFE-1", reviewed_at=None)])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is False
        assert result["counts"]["MISSING_REVIEWED_AT"] == 1

    def test_5_exact_source_reference_required_missing_pm(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([])  # no matching pm_occurrence at all
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is False
        assert result["counts"]["MISSING_PM_OCCURRENCE"] == 1

    def test_6_wrong_candidate_type_rejected(self):
        staging = FakeStagingRepo([_candidate("DFE-1", detected_document_type="HISTORICAL_CMON_READING_CANDIDATE")])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["results"] == []  # excluded before even becoming a target

    def test_7_missing_pm_rejected(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["counts"]["MISSING_PM_OCCURRENCE"] == 1

    def test_8_duplicate_source_reference_rejected(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([
            _pm_row("DFE-1", pm_occurrence_code="PMOCC-A"),
            {**_pm_row("DFE-1", pm_occurrence_code="PMOCC-B")},
        ])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is False
        assert result["counts"]["DUPLICATE_SOURCE_REFERENCE"] == 1

    def test_9_asset_date_conflict_rejected(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([
            _pm_row("DFE-1"),
            {"pm_occurrence_code": "PMOCC-OTHER", "source_reference": "document_field_extraction:DFE-OTHER",
             "asset_code": "110-P-9A", "occurrence_date": "2026-07-01", "workflow_status": "DRAFT"},
        ])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is False
        assert result["counts"]["ASSET_DATE_CONFLICT"] == 1

    def test_10_invalid_canonical_pump_rejected(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")], valid_pump_tags=set())
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is False
        assert result["counts"]["INVALID_PUMP"] == 1

    def test_11_non_recovery_draft_pm_excluded(self):
        # a pm_occurrence in DRAFT with no matching recovery candidate at
        # all is simply never touched -- the population is entirely
        # candidate-driven, never a broad workflow_status=DRAFT scan.
        staging = FakeStagingRepo([])
        pm_repo = FakePMOccurrenceRepo([
            {"pm_occurrence_code": "PMOCC-ORDINARY", "source_reference": None,
             "asset_code": "110-P-9A", "occurrence_date": "2026-07-01", "workflow_status": "DRAFT"},
        ])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["results"] == []
        assert pm_repo.find_by_source_references_calls == []

    def test_12_ordinary_digital_pm_cannot_use_historical_bypass(self):
        # An ordinary PM occurrence (provenance MANUAL, no source_
        # reference pointing at a recovery candidate) is structurally
        # unreachable: it is never looked up by fetch_finalization_
        # targets/find_by_source_references at all.
        staging = FakeStagingRepo([])
        pm_repo = FakePMOccurrenceRepo([])
        result = validate_finalization_batch(staging, pm_repo)
        assert result == {"results": [], "counts": {}, "all_eligible": True, "eligible_pm_occurrence_codes": []}

    def test_already_finalized_is_a_safe_idempotent_outcome(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1", workflow_status="FINALIZED")])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is True
        assert result["counts"] == {"ALREADY_FINALIZED": 1}
        assert result["eligible_pm_occurrence_codes"] == []  # never re-written

    def test_not_draft_and_not_finalized_rejected(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1", workflow_status="SUBMITTED")])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is False
        assert result["counts"]["NOT_DRAFT"] == 1

    def test_mixed_eligible_and_already_finalized_is_all_eligible(self):
        staging = FakeStagingRepo([
            _candidate("DFE-1"),
            _candidate("DFE-2", extracted_fields={"occurrence_date": "2026-07-02", "candidate_identity_v2": "HASH-DFE-2"}),
        ])
        pm_repo = FakePMOccurrenceRepo([
            _pm_row("DFE-1", workflow_status="FINALIZED"),
            _pm_row("DFE-2", occurrence_date="2026-07-02"),
        ])
        result = validate_finalization_batch(staging, pm_repo)
        assert result["all_eligible"] is True
        assert result["counts"] == {"ALREADY_FINALIZED": 1, "ELIGIBLE": 1}
        assert result["eligible_pm_occurrence_codes"] == ["PMOCC-DFE-2"]

    def test_19_status_query_count_bounded_not_per_candidate(self):
        # MWO-LTSA-HISTORICAL-PM-FINALIZATION-001 -- 540-scale proof: a
        # small, N-independent number of repository calls (list_by_
        # status, find_by_source_references, find_by_asset_dates,
        # find_valid_pump_tags -- 4 total), never one per candidate.
        # One distinct calendar date per candidate (matches the real
        # production 540's own verified invariant: zero internal
        # (asset, date) duplicates) -- a modulo-based date generator
        # would alias multiple candidates onto the same date for the
        # same asset and falsely trip the ASSET_DATE_CONFLICT check.
        base_date = date(2020, 1, 1)
        dates = [(base_date + timedelta(days=i)).isoformat() for i in range(540)]
        candidates = [
            _candidate(f"DFE-{i}", extracted_fields={"occurrence_date": dates[i], "candidate_identity_v2": f"HASH-{i}"})
            for i in range(540)
        ]
        staging = FakeStagingRepo(candidates)
        pm_rows = [
            _pm_row(f"DFE-{i}", occurrence_date=dates[i])
            for i in range(540)
        ]
        pm_repo = FakePMOccurrenceRepo(pm_rows)

        result = validate_finalization_batch(staging, pm_repo)

        assert result["all_eligible"] is True
        assert result["counts"] == {"ELIGIBLE": 540}
        assert len(staging.list_by_status_calls) == 1
        assert len(pm_repo.find_by_source_references_calls) == 1
        assert len(pm_repo.find_by_source_references_calls[0]) == 540
        assert len(pm_repo.find_by_asset_dates_calls) == 1
        assert len(pm_repo.find_valid_pump_tags_calls) == 1
        total_calls = (
            len(staging.list_by_status_calls)
            + len(pm_repo.find_by_source_references_calls)
            + len(pm_repo.find_by_asset_dates_calls)
            + len(pm_repo.find_valid_pump_tags_calls)
        )
        assert total_calls == 4


class TestFinalizationReadiness:
    def test_pre_finalization_expected_shape(self):
        candidates = [_candidate(f"DFE-{i}", extracted_fields={"occurrence_date": f"2026-01-{i + 1:02d}", "candidate_identity_v2": f"HASH-{i}"}) for i in range(3)]
        staging = FakeStagingRepo(candidates)
        pm_repo = FakePMOccurrenceRepo([_pm_row(f"DFE-{i}", occurrence_date=f"2026-01-{i + 1:02d}") for i in range(3)])
        result = finalization_readiness(staging, pm_repo)
        assert result == {
            "target_count": 3, "draft_count": 3, "finalized_count": 0,
            "invalid_count": 0, "finalization_ready": True,
        }

    def test_post_finalization_expected_shape(self):
        candidates = [_candidate(f"DFE-{i}", extracted_fields={"occurrence_date": f"2026-01-{i + 1:02d}", "candidate_identity_v2": f"HASH-{i}"}) for i in range(3)]
        staging = FakeStagingRepo(candidates)
        pm_repo = FakePMOccurrenceRepo([_pm_row(f"DFE-{i}", occurrence_date=f"2026-01-{i + 1:02d}", workflow_status="FINALIZED") for i in range(3)])
        result = finalization_readiness(staging, pm_repo)
        assert result == {
            "target_count": 3, "draft_count": 0, "finalized_count": 3,
            "invalid_count": 0, "finalization_ready": False,
        }

    def test_invalid_count_reflects_ineligible_targets(self):
        staging = FakeStagingRepo([_candidate("DFE-1", reviewed_by=None)])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")])
        result = finalization_readiness(staging, pm_repo)
        assert result["target_count"] == 1
        assert result["invalid_count"] == 1
        assert result["finalization_ready"] is False


class TestFinalizeHistoricalPmBatch:
    def test_13_atomic_rollback_on_one_invalid_member(self):
        staging = FakeStagingRepo([
            _candidate("DFE-1"),
            _candidate("DFE-2", reviewed_by=None, extracted_fields={"occurrence_date": "2026-07-02", "candidate_identity_v2": "HASH-DFE-2"}),
        ])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1"), _pm_row("DFE-2", occurrence_date="2026-07-02")])
        result = finalize_historical_pm_batch(staging, pm_repo, finalized_by="actor-1")
        assert result["status"] == "REJECTED_PRECHECK_FAILED"
        assert result["finalized_count"] == 0
        assert pm_repo.finalize_calls == []  # nothing written -- no partial finalization

    def test_14_authenticated_actor_used(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")])
        finalize_historical_pm_batch(staging, pm_repo, finalized_by="actor-42")
        assert pm_repo.finalize_calls[0]["finalized_by"] == "actor-42"

    def test_16_audit_generated_exactly_once_per_finalized_pm(self):
        # the atomic method itself is what writes one record_change_
        # history row per RETURNING row (real-DB behavior, exercised in
        # test_pm_occurrence_repository_real_db.py) -- at this layer,
        # verify the service calls the atomic write exactly ONCE per
        # batch (never once per candidate), with exactly the eligible
        # codes.
        staging = FakeStagingRepo([_candidate("DFE-1"), _candidate("DFE-2", extracted_fields={"occurrence_date": "2026-07-02", "candidate_identity_v2": "HASH-DFE-2"})])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1"), _pm_row("DFE-2", occurrence_date="2026-07-02")])
        result = finalize_historical_pm_batch(staging, pm_repo, finalized_by="actor-1")
        assert result["status"] == "FINALIZED"
        assert result["finalized_count"] == 2
        assert len(pm_repo.finalize_calls) == 1
        assert set(pm_repo.finalize_calls[0]["pm_occurrence_codes"]) == {"PMOCC-DFE-1", "PMOCC-DFE-2"}

    def test_17_retry_after_full_success_is_zero_mutation(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1", workflow_status="FINALIZED")])
        result = finalize_historical_pm_batch(staging, pm_repo, finalized_by="actor-1")
        assert result["status"] == "FINALIZED"
        assert result["finalized_count"] == 0
        assert pm_repo.finalize_calls == []  # atomic write never even called

    def test_atomic_transaction_failure_is_reported_not_raised(self):
        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = FakePMOccurrenceRepo([_pm_row("DFE-1")])
        pm_repo.raise_on_atomic = RuntimeError("db exploded")
        result = finalize_historical_pm_batch(staging, pm_repo, finalized_by="actor-1")
        assert result["status"] == "REJECTED_ATOMIC_TRANSACTION_FAILED"
        assert "db exploded" in result["error"]

    def test_atomic_row_count_mismatch_raises(self):
        class ShortRepo(FakePMOccurrenceRepo):
            def finalize_historical_batch_atomic(self, pm_occurrence_codes, *, finalized_by):
                return []

        staging = FakeStagingRepo([_candidate("DFE-1")])
        pm_repo = ShortRepo([_pm_row("DFE-1")])
        with pytest.raises(FinalizationBatchError):
            finalize_historical_pm_batch(staging, pm_repo, finalized_by="actor-1")

    def test_zero_targets_is_a_clean_zero_mutation_success(self):
        staging = FakeStagingRepo([])
        pm_repo = FakePMOccurrenceRepo([])
        result = finalize_historical_pm_batch(staging, pm_repo, finalized_by="actor-1")
        assert result["status"] == "FINALIZED"
        assert result["finalized_count"] == 0
        assert pm_repo.finalize_calls == []
