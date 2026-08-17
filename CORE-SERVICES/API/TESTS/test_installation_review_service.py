"""MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 -- pure-logic coverage for
installation_review_service.py: pump/seal matching, the review-status gate,
the status state machine, and the document_field_extraction ->
installation_report promotion (Save) path. No database, no fixtures beyond
plain dicts -- the module itself performs zero I/O.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from installation_review_service import (  # noqa: E402
    STATUS_PENDING_REVIEW,
    STATUS_REJECTED,
    STATUS_REVIEWED,
    STATUS_SAVED,
    InvalidReviewTransition,
    UnresolvedIdentityError,
    build_installation_report_row,
    match_pump,
    match_seal,
    resolve_pump_review_gate,
    validate_status_transition,
)


class TestMatchPump:
    def test_single_candidate_matches(self):
        result = match_pump("211-P-14B", [{"tag_number": "211-P-14B"}])
        assert result.outcome == "MATCHED"
        assert result.matched_id == "211-P-14B"
        assert not result.needs_review

    def test_unknown_pump_no_candidates(self):
        result = match_pump("999-P-99Z", [])
        assert result.outcome == "NOT_FOUND"
        assert result.needs_review

    def test_blank_plant_equip_no_is_not_found_never_guessed(self):
        result = match_pump(None, [{"tag_number": "211-P-14B"}])
        assert result.outcome == "NOT_FOUND"
        result_blank = match_pump("   ", [{"tag_number": "211-P-14B"}])
        assert result_blank.outcome == "NOT_FOUND"

    def test_ambiguous_multiple_candidates(self):
        result = match_pump(
            "211-P-2",
            [{"tag_number": "211-P-2A"}, {"tag_number": "211-P-2B"}],
        )
        assert result.outcome == "AMBIGUOUS"
        assert result.matched_id is None
        assert result.candidate_ids == ("211-P-2A", "211-P-2B")
        assert result.needs_review


class TestMatchSeal:
    def test_matched(self):
        result = match_seal("LTSA-SEAL-T15W", [{"seal_code": "LTSA-SEAL-T15W"}])
        assert result.outcome == "MATCHED"

    def test_no_seal_identifier_on_report_is_not_found_not_an_error(self):
        # sampleInstallations.js's own real seed row: descriptive text only,
        # no seal_registry identifier -- a legitimate NOT_FOUND, not a bug.
        result = match_seal(None, [])
        assert result.outcome == "NOT_FOUND"

    def test_ambiguous(self):
        result = match_seal(
            "T15W",
            [{"seal_code": "LTSA-SEAL-T15W-A"}, {"seal_code": "LTSA-SEAL-T15W-B"}],
        )
        assert result.outcome == "AMBIGUOUS"


class TestResolvePumpReviewGate:
    def test_matched_high_confidence_does_not_need_review(self):
        matched = match_pump("211-P-14B", [{"tag_number": "211-P-14B"}])
        assert resolve_pump_review_gate(matched, detected_document_type_confidence=0.97) is False

    def test_matched_low_confidence_still_needs_review(self):
        matched = match_pump("211-P-14B", [{"tag_number": "211-P-14B"}])
        assert resolve_pump_review_gate(matched, detected_document_type_confidence=0.4) is True

    def test_ambiguous_needs_review_regardless_of_confidence(self):
        ambiguous = match_pump("211-P-2", [{"tag_number": "211-P-2A"}, {"tag_number": "211-P-2B"}])
        assert resolve_pump_review_gate(ambiguous, detected_document_type_confidence=0.99) is True

    def test_not_found_needs_review(self):
        not_found = match_pump("999-P-99Z", [])
        assert resolve_pump_review_gate(not_found, detected_document_type_confidence=0.99) is True

    def test_missing_confidence_needs_review(self):
        matched = match_pump("211-P-14B", [{"tag_number": "211-P-14B"}])
        assert resolve_pump_review_gate(matched, detected_document_type_confidence=None) is True


class TestValidateStatusTransition:
    @pytest.mark.parametrize(
        "current,next_status",
        [
            (STATUS_PENDING_REVIEW, STATUS_REVIEWED),
            (STATUS_PENDING_REVIEW, STATUS_REJECTED),
            (STATUS_REVIEWED, STATUS_SAVED),
            (STATUS_REVIEWED, STATUS_REJECTED),
            (STATUS_REVIEWED, STATUS_PENDING_REVIEW),
        ],
    )
    def test_allowed_transitions(self, current, next_status):
        assert validate_status_transition(current, next_status) is True

    @pytest.mark.parametrize(
        "current,next_status",
        [
            (STATUS_PENDING_REVIEW, STATUS_SAVED),  # cannot skip human review
            (STATUS_SAVED, STATUS_PENDING_REVIEW),  # SAVED is terminal
            (STATUS_SAVED, STATUS_REJECTED),
            (STATUS_REJECTED, STATUS_PENDING_REVIEW),  # REJECTED is terminal
            (STATUS_REJECTED, STATUS_REVIEWED),
        ],
    )
    def test_forbidden_transitions(self, current, next_status):
        assert validate_status_transition(current, next_status) is False


class TestBuildInstallationReportRow:
    def _reviewed_extraction(self, **overrides):
        base = {
            "status": STATUS_REVIEWED,
            "pump_tag_number": "211-P-14B",
            "seal_code": "LTSA-SEAL-T15W-TEST",
            "extracted_fields": {
                "reportNo": {"value": "001/INSTL /TAP/01-2026", "confidence": 0.95},
                "plant": {"value": "HCC", "confidence": 0.9},
            },
            "reviewed_fields": {},
        }
        base.update(overrides)
        return base

    def test_approval_creates_canonical_row(self):
        row = build_installation_report_row(self._reviewed_extraction(), installation_code="INSTL-100")
        assert row["installation_code"] == "INSTL-100"
        assert row["plant_equip_no"] == "211-P-14B"
        assert row["seal_code"] == "LTSA-SEAL-T15W-TEST"
        assert row["report_no"] == "001/INSTL /TAP/01-2026"
        assert row["plant"] == "HCC"

    def test_reviewed_fields_win_over_extracted_fields(self):
        extraction = self._reviewed_extraction(
            reviewed_fields={"plant": "HCC (corrected)"},
        )
        row = build_installation_report_row(extraction, installation_code="INSTL-101")
        assert row["plant"] == "HCC (corrected)"

    def test_rejected_draft_can_never_be_saved_no_canonical_mutation(self):
        extraction = self._reviewed_extraction(status=STATUS_REJECTED)
        with pytest.raises(InvalidReviewTransition):
            build_installation_report_row(extraction, installation_code="INSTL-SHOULD-NOT-EXIST")

    def test_pending_review_draft_cannot_be_saved(self):
        extraction = self._reviewed_extraction(status=STATUS_PENDING_REVIEW)
        with pytest.raises(InvalidReviewTransition):
            build_installation_report_row(extraction, installation_code="INSTL-SHOULD-NOT-EXIST")

    def test_unmatched_pump_can_never_be_saved_even_if_reviewed(self):
        # Never fabricate a pump match -- REVIEWED alone is not sufficient.
        extraction = self._reviewed_extraction(pump_tag_number=None)
        with pytest.raises(UnresolvedIdentityError):
            build_installation_report_row(extraction, installation_code="INSTL-SHOULD-NOT-EXIST")

    def test_seal_code_omitted_when_unmatched_never_fabricated(self):
        extraction = self._reviewed_extraction(seal_code=None)
        row = build_installation_report_row(extraction, installation_code="INSTL-102")
        assert "seal_code" not in row

    def test_does_not_touch_or_return_any_pump_master_fields(self):
        # This function has zero DB access and returns only report-scoped
        # columns -- it cannot silently overwrite ltsa_pumps by construction.
        row = build_installation_report_row(self._reviewed_extraction(), installation_code="INSTL-103")
        assert "area" not in row
        assert "criticality" not in row
        assert "id" not in row
