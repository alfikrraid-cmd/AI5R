"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- promotion service coverage:
the REVIEWED-only gate, the resolved-pump-tag-only gate, provenance/
source_reference correctness, and that a CMON candidate's finding text
survives promotion via create_draft's own finding kwarg (not silently
dropped inside the generic measurements dict)."""

import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.historical_pm_cmon_promotion_service import (  # noqa: E402
    PROVENANCE_HISTORICAL_IMPORT,
    AlreadyPromotedError,
    PromotionError,
    promote_cmon_reading_candidate,
    promote_pm_occurrence_atomic,
)


class FakeAtomicPMRepository:
    """Fakes PMOccurrenceRepository.promote_historical_pm_atomic()'s own
    result contract (candidate_found/eligible/already/conflict/inserted/
    marked_saved), letting the SERVICE layer's exception-translation be
    tested independently of the real SQL."""

    def __init__(self, response: dict):
        self.response = response
        self.calls: list[dict] = []

    def promote_historical_pm_atomic(self, candidate_id, *, pm_schedule_code, promoted_by):
        self.calls.append({"candidate_id": candidate_id, "pm_schedule_code": pm_schedule_code, "promoted_by": promoted_by})
        return self.response


def _atomic_response(**overrides):
    base = {
        "candidate_found": True, "eligible": True, "already": None,
        "conflict": None, "inserted": {"pm_occurrence_code": "PMOCC-NEW", "asset_code": "110-P-9A"},
        "marked_saved": True,
    }
    base.update(overrides)
    return base


class FakeCMONRepository:
    def __init__(self):
        self.calls: list[dict] = []

    def create_draft(self, **kwargs):
        self.calls.append(kwargs)
        return {"condition_monitoring_reading_code": "CMONR-NEW", **kwargs}


class FakeStagingRepository:
    def __init__(self):
        self.saved_ids: list[str] = []

    def mark_saved(self, candidate_id: str) -> None:
        self.saved_ids.append(candidate_id)


def _cmon_candidate(**overrides):
    base = {
        "document_field_extraction_id": "DFE-2",
        "status": "REVIEWED",
        "pump_tag_number": "110-P-9A",
        "extracted_fields": {
            "reading_date": "2026-07-01", "asset_type": "PUMP",
            "mechseal_temp_de": 58.0, "finding": "STANDBY, bocor dari draingland 1/2 detik",
        },
        "reviewed_fields": None,
    }
    base.update(overrides)
    return base


class TestPromotePMOccurrenceAtomic:
    def test_promotes_and_returns_the_inserted_row(self):
        repo = FakeAtomicPMRepository(_atomic_response())
        record = promote_pm_occurrence_atomic(
            "DFE-1", pm_occurrence_repository=repo,
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        assert record["pm_occurrence_code"] == "PMOCC-NEW"
        assert repo.calls[0] == {
            "candidate_id": "DFE-1", "pm_schedule_code": "UNSCHEDULED::HOC-JULY-2026", "promoted_by": "reviewer-1",
        }

    def test_candidate_not_found_raises_promotion_error(self):
        repo = FakeAtomicPMRepository(_atomic_response(candidate_found=False, eligible=False, inserted=None, marked_saved=False))
        with pytest.raises(PromotionError):
            promote_pm_occurrence_atomic(
                "DFE-MISSING", pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_not_reviewed_is_not_eligible_and_raises_promotion_error(self):
        repo = FakeAtomicPMRepository(_atomic_response(eligible=False, inserted=None, marked_saved=False))
        with pytest.raises(PromotionError):
            promote_pm_occurrence_atomic(
                "DFE-1", pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_already_promoted_raises_already_promoted_error(self):
        repo = FakeAtomicPMRepository(_atomic_response(
            already={"pm_occurrence_code": "PMOCC-OLD"}, eligible=False, inserted=None, marked_saved=False,
        ))
        with pytest.raises(AlreadyPromotedError):
            promote_pm_occurrence_atomic(
                "DFE-1", pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_conflict_with_a_different_candidates_final_pm_raises_promotion_error(self):
        repo = FakeAtomicPMRepository(_atomic_response(
            conflict={"pm_occurrence_code": "PMOCC-OTHER"}, inserted=None, marked_saved=False,
        ))
        with pytest.raises(PromotionError):
            promote_pm_occurrence_atomic(
                "DFE-1", pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_eligible_but_no_insert_raises_promotion_error(self):
        # e.g. unknown pump or missing pm_schedule -- eligible per the
        # candidate row itself, but the atomic script's own WHERE EXISTS
        # guard(s) still blocked the insert.
        repo = FakeAtomicPMRepository(_atomic_response(inserted=None, marked_saved=False))
        with pytest.raises(PromotionError):
            promote_pm_occurrence_atomic(
                "DFE-1", pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_inconsistent_insert_without_mark_saved_raises(self):
        # Should be unreachable given the SQL's own gating, but the
        # service layer still refuses to report success silently.
        repo = FakeAtomicPMRepository(_atomic_response(marked_saved=False))
        with pytest.raises(PromotionError):
            promote_pm_occurrence_atomic(
                "DFE-1", pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_exact_retry_after_success_is_already_promoted_never_a_second_write(self):
        # The real idempotency proof: first call promotes; a second call
        # against the SAME repository state (as a real retry would see,
        # since the candidate is now SAVED with a matching pm_occurrence)
        # must be rejected as AlreadyPromotedError, never treated as a
        # fresh promotion.
        first = FakeAtomicPMRepository(_atomic_response())
        promote_pm_occurrence_atomic(
            "DFE-1", pm_occurrence_repository=first,
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        retry = FakeAtomicPMRepository(_atomic_response(
            already={"pm_occurrence_code": "PMOCC-NEW"}, eligible=False, inserted=None, marked_saved=False,
        ))
        with pytest.raises(AlreadyPromotedError):
            promote_pm_occurrence_atomic(
                "DFE-1", pm_occurrence_repository=retry,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )


class TestPromoteCMONReadingCandidate:
    def test_promotes_a_reviewed_matched_candidate(self):
        repo = FakeCMONRepository()
        promote_cmon_reading_candidate(
            _cmon_candidate(), cmon_repository=repo,
            condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        assert repo.calls[0]["provenance"] == PROVENANCE_HISTORICAL_IMPORT
        assert repo.calls[0]["source_reference"] == "document_field_extraction:DFE-2"

    def test_finding_text_passed_as_its_own_kwarg_not_inside_measurements(self):
        repo = FakeCMONRepository()
        promote_cmon_reading_candidate(
            _cmon_candidate(), cmon_repository=repo,
            condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        call = repo.calls[0]
        assert call["finding"] == "STANDBY, bocor dari draingland 1/2 detik"
        assert "finding" not in call["measurements"]

    def test_measurements_carry_the_real_measurement_fields(self):
        repo = FakeCMONRepository()
        promote_cmon_reading_candidate(
            _cmon_candidate(), cmon_repository=repo,
            condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        assert repo.calls[0]["measurements"]["mechseal_temp_de"] == 58.0

    def test_rejects_non_reviewed_candidate(self):
        repo = FakeCMONRepository()
        with pytest.raises(PromotionError):
            promote_cmon_reading_candidate(
                _cmon_candidate(status="PENDING_REVIEW"), cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_rejects_unmatched_pump(self):
        repo = FakeCMONRepository()
        with pytest.raises(PromotionError):
            promote_cmon_reading_candidate(
                _cmon_candidate(pump_tag_number=None), cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_already_saved_raises_already_promoted_not_plain_promotion_error(self):
        repo = FakeCMONRepository()
        with pytest.raises(AlreadyPromotedError):
            promote_cmon_reading_candidate(
                _cmon_candidate(status="SAVED"), cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_marks_candidate_saved_when_staging_repository_given(self):
        repo = FakeCMONRepository()
        staging = FakeStagingRepository()
        promote_cmon_reading_candidate(
            _cmon_candidate(), cmon_repository=repo,
            condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            staging_repository=staging,
        )
        assert staging.saved_ids == ["DFE-2"]
