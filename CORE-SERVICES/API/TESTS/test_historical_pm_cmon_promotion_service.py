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
    promote_pm_occurrence_candidate,
)


class FakePMRepository:
    def __init__(self):
        self.calls: list[dict] = []

    def create_draft(self, **kwargs):
        self.calls.append(kwargs)
        return {"pm_occurrence_code": "PMOCC-NEW", **kwargs}


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


def _pm_candidate(**overrides):
    base = {
        "document_field_extraction_id": "DFE-1",
        "status": "REVIEWED",
        "pump_tag_number": "110-P-9A",
        "extracted_fields": {"occurrence_date": "2026-07-01", "asset_type": "PUMP"},
        "reviewed_fields": None,
    }
    base.update(overrides)
    return base


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


class TestPromotePMOccurrenceCandidate:
    def test_promotes_a_reviewed_matched_candidate(self):
        repo = FakePMRepository()
        promote_pm_occurrence_candidate(
            _pm_candidate(), pm_occurrence_repository=repo,
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        assert repo.calls[0]["provenance"] == PROVENANCE_HISTORICAL_IMPORT
        assert repo.calls[0]["source_reference"] == "document_field_extraction:DFE-1"
        assert repo.calls[0]["asset_code"] == "110-P-9A"

    def test_rejects_non_reviewed_candidate(self):
        repo = FakePMRepository()
        with pytest.raises(PromotionError):
            promote_pm_occurrence_candidate(
                _pm_candidate(status="PENDING_REVIEW"), pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )
        assert repo.calls == []

    def test_rejects_unmatched_pump(self):
        repo = FakePMRepository()
        with pytest.raises(PromotionError):
            promote_pm_occurrence_candidate(
                _pm_candidate(pump_tag_number=None), pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )
        assert repo.calls == []

    def test_already_saved_raises_already_promoted(self):
        repo = FakePMRepository()
        with pytest.raises(AlreadyPromotedError):
            promote_pm_occurrence_candidate(
                _pm_candidate(status="SAVED"), pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_reviewed_fields_take_precedence_over_extracted_fields(self):
        repo = FakePMRepository()
        candidate = _pm_candidate(reviewed_fields={"occurrence_date": "2026-07-02", "asset_type": "PUMP"})
        promote_pm_occurrence_candidate(
            candidate, pm_occurrence_repository=repo,
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        assert repo.calls[0]["occurrence_date"] == "2026-07-02"

    def test_marks_candidate_saved_when_staging_repository_given(self):
        repo = FakePMRepository()
        staging = FakeStagingRepository()
        promote_pm_occurrence_candidate(
            _pm_candidate(), pm_occurrence_repository=repo,
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            staging_repository=staging,
        )
        assert staging.saved_ids == ["DFE-1"]

    def test_does_not_mark_saved_when_staging_repository_omitted(self):
        repo = FakePMRepository()
        # Must not raise just because staging_repository wasn't passed.
        promote_pm_occurrence_candidate(
            _pm_candidate(), pm_occurrence_repository=repo,
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )

    def test_second_promotion_after_mark_saved_is_rejected_never_duplicated(self):
        # The real idempotency proof: promote once (marks SAVED via the
        # staging repository), then attempt to promote the SAME candidate
        # dict again with status manually advanced to SAVED (as a real
        # staging_repository.find_by_id() re-read would show) -- must be
        # rejected, never silently creating a second canonical record.
        repo = FakePMRepository()
        staging = FakeStagingRepository()
        promote_pm_occurrence_candidate(
            _pm_candidate(), pm_occurrence_repository=repo,
            pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            staging_repository=staging,
        )
        assert len(repo.calls) == 1

        with pytest.raises(AlreadyPromotedError):
            promote_pm_occurrence_candidate(
                _pm_candidate(status="SAVED"), pm_occurrence_repository=repo,
                pm_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
                staging_repository=staging,
            )
        assert len(repo.calls) == 1  # no second canonical write


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
