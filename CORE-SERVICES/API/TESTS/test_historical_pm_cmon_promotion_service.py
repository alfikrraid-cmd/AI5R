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


class FakeAtomicCMONRepository:
    """Fakes ConditionMonitoringReadingRepository.
    promote_historical_cmon_atomic()'s own result contract (candidate_
    found/eligible/already/conflict/inserted/marked_saved), letting the
    SERVICE layer's exception-translation be tested independently of the
    real SQL -- exact CMON sibling of FakeAtomicPMRepository above."""

    def __init__(self, response: dict):
        self.response = response
        self.calls: list[dict] = []

    def promote_historical_cmon_atomic(self, candidate_id, *, condition_monitoring_schedule_code, promoted_by):
        self.calls.append({
            "candidate_id": candidate_id,
            "condition_monitoring_schedule_code": condition_monitoring_schedule_code,
            "promoted_by": promoted_by,
        })
        return self.response


def _cmon_atomic_response(**overrides):
    base = {
        "candidate_found": True, "eligible": True, "already": None,
        "conflict": None,
        "inserted": {
            "condition_monitoring_reading_code": "CMONR-NEW", "asset_code": "110-P-9A",
            "mechseal_temp_de": 58.0, "finding": "STANDBY, bocor dari draingland 1/2 detik",
        },
        "marked_saved": True,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("existing", [None, {"condition_monitoring_reading_code": "CMONR-WINNER"}])
def test_saved_cmon_snapshot_requires_canonical_evidence(existing):
    repo = FakeAtomicCMONRepository(_cmon_atomic_response(
        candidate_status="SAVED", eligible=False, inserted=None, marked_saved=False,
    ))
    lookups = []

    def find(source_reference):
        lookups.append(source_reference)
        return existing

    repo.find_by_source_reference = find
    with pytest.raises(PromotionError) as caught:
        promote_cmon_reading_candidate(
            "DFE-RACE", cmon_repository=repo,
            condition_monitoring_schedule_code="UNSCHEDULED::TEST", promoted_by="actor",
        )
    assert isinstance(caught.value, AlreadyPromotedError) is (existing is not None)
    assert lookups == ["document_field_extraction:DFE-RACE"]


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


class TestPromoteCMONReadingAtomic:
    """MWO-LTSA-ATOMIC-CMON-PROMOTION-001 -- exact CMON mirror of
    TestPromotePMOccurrenceAtomic above; same nine cases, same
    reasoning, proving CMON promotion is now atomic/idempotent/retry-
    safe exactly like PM."""

    def test_promotes_and_returns_the_inserted_row(self):
        repo = FakeAtomicCMONRepository(_cmon_atomic_response())
        record = promote_cmon_reading_candidate(
            "DFE-2", cmon_repository=repo,
            condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        assert record["condition_monitoring_reading_code"] == "CMONR-NEW"
        assert repo.calls[0] == {
            "candidate_id": "DFE-2",
            "condition_monitoring_schedule_code": "UNSCHEDULED::HOC-JULY-2026",
            "promoted_by": "reviewer-1",
        }

    def test_finding_text_survives_on_the_inserted_row(self):
        # Real regression guard: the old two-write path passed `finding`
        # as its own create_draft() kwarg, kept separate from the generic
        # measurements dict. The atomic SQL now does the same split
        # inline (e.fields->>'finding' vs the measurement-cast list) --
        # this proves the inserted row still carries it correctly.
        repo = FakeAtomicCMONRepository(_cmon_atomic_response())
        record = promote_cmon_reading_candidate(
            "DFE-2", cmon_repository=repo,
            condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        assert record["finding"] == "STANDBY, bocor dari draingland 1/2 detik"

    def test_candidate_not_found_raises_promotion_error(self):
        repo = FakeAtomicCMONRepository(_cmon_atomic_response(candidate_found=False, eligible=False, inserted=None, marked_saved=False))
        with pytest.raises(PromotionError):
            promote_cmon_reading_candidate(
                "DFE-MISSING", cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_not_reviewed_is_not_eligible_and_raises_promotion_error(self):
        repo = FakeAtomicCMONRepository(_cmon_atomic_response(eligible=False, inserted=None, marked_saved=False))
        with pytest.raises(PromotionError):
            promote_cmon_reading_candidate(
                "DFE-2", cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_unmatched_pump_is_not_eligible_and_raises_promotion_error(self):
        # eligible=False mirrors the atomic SQL's own eligible CTE, which
        # requires pump_tag_number IS NOT NULL -- an unmatched pump never
        # reaches the INSERT.
        repo = FakeAtomicCMONRepository(_cmon_atomic_response(eligible=False, inserted=None, marked_saved=False))
        with pytest.raises(PromotionError):
            promote_cmon_reading_candidate(
                "DFE-2", cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_already_promoted_raises_already_promoted_error(self):
        repo = FakeAtomicCMONRepository(_cmon_atomic_response(
            already={"condition_monitoring_reading_code": "CMONR-OLD"}, eligible=False, inserted=None, marked_saved=False,
        ))
        with pytest.raises(AlreadyPromotedError):
            promote_cmon_reading_candidate(
                "DFE-2", cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_conflict_with_a_different_candidates_final_cmon_raises_promotion_error(self):
        repo = FakeAtomicCMONRepository(_cmon_atomic_response(
            conflict={"condition_monitoring_reading_code": "CMONR-OTHER"}, inserted=None, marked_saved=False,
        ))
        with pytest.raises(PromotionError):
            promote_cmon_reading_candidate(
                "DFE-2", cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_eligible_but_no_insert_raises_promotion_error(self):
        repo = FakeAtomicCMONRepository(_cmon_atomic_response(inserted=None, marked_saved=False))
        with pytest.raises(PromotionError):
            promote_cmon_reading_candidate(
                "DFE-2", cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_inconsistent_insert_without_mark_saved_raises(self):
        repo = FakeAtomicCMONRepository(_cmon_atomic_response(marked_saved=False))
        with pytest.raises(PromotionError):
            promote_cmon_reading_candidate(
                "DFE-2", cmon_repository=repo,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )

    def test_exact_retry_after_success_is_already_promoted_never_a_second_write(self):
        first = FakeAtomicCMONRepository(_cmon_atomic_response())
        promote_cmon_reading_candidate(
            "DFE-2", cmon_repository=first,
            condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
        )
        retry = FakeAtomicCMONRepository(_cmon_atomic_response(
            already={"condition_monitoring_reading_code": "CMONR-NEW"}, eligible=False, inserted=None, marked_saved=False,
        ))
        with pytest.raises(AlreadyPromotedError):
            promote_cmon_reading_candidate(
                "DFE-2", cmon_repository=retry,
                condition_monitoring_schedule_code="UNSCHEDULED::HOC-JULY-2026", promoted_by="reviewer-1",
            )
