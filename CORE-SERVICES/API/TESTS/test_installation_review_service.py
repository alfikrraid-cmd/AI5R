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
    CRITICAL_PROVENANCE_FIELDS,
    STATUS_PENDING_REVIEW,
    STATUS_REJECTED,
    STATUS_REVIEWED,
    STATUS_SAVED,
    InvalidReviewTransition,
    UnresolvedIdentityError,
    build_installation_report_row,
    match_pump,
    match_seal,
    missing_field_provenance,
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

    # MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- Phase 10
    # round-trip: every structural field (date-grouped site activities,
    # DE/NDE observation entries, variable-shape BOM, post-installation
    # readings) survives extract -> review -> promote without loss.
    def test_round_trip_preserves_date_grouped_site_activities_verbatim(self):
        site_activities = [
            {"date": "January 23-24, 2026", "activities": ["Work permit.", "Dismantling the gland plate."]},
            {"date": "January 28, 2026", "activities": ["Work permit.", "Monitoring pump Tag No. 211-P-2A"]},
        ]
        extraction = self._reviewed_extraction(reviewed_fields={"siteActivities": site_activities})
        row = build_installation_report_row(extraction, installation_code="INSTL-104")
        assert row["site_activities"] == site_activities

    def test_round_trip_preserves_de_nde_observation_entries_without_collapsing(self):
        gland_observation = [
            {"item": "Inboard Side / Outboard Side re-used", "checkedDE": True, "checkedNDE": False},
        ]
        extraction = self._reviewed_extraction(reviewed_fields={"glandObservation": gland_observation})
        row = build_installation_report_row(extraction, installation_code="INSTL-105")
        assert row["gland_observation"] == gland_observation
        assert row["gland_observation"][0]["checkedDE"] is True
        assert row["gland_observation"][0]["checkedNDE"] is False

    def test_round_trip_preserves_variable_bill_of_material_shape(self):
        bom = [
            {"item": 1, "drawingNumber": "F 1250 443", "materialCode": "9205", "description": "Mating Ring", "material": "Tungsten Carbide", "qty": 1, "workRequired": "Replace"},
        ]
        extraction = self._reviewed_extraction(reviewed_fields={"billOfMaterial": bom})
        row = build_installation_report_row(extraction, installation_code="INSTL-106")
        assert row["bill_of_material"] == bom

    def test_round_trip_preserves_post_installation_readings(self):
        readings = [
            {"measurement": "Mechanical Seal Gland Temperature", "de": "107", "nde": "115", "unit": "°C", "dateTime": "2026-01-28T10:15:00"},
        ]
        extraction = self._reviewed_extraction(reviewed_fields={"postInstallationReadings": readings})
        row = build_installation_report_row(extraction, installation_code="INSTL-107")
        assert row["post_installation_readings"] == readings

    def test_round_trip_omits_post_installation_readings_key_when_absent(self):
        # Never fabricates an empty readings list for a report that has none.
        row = build_installation_report_row(self._reviewed_extraction(), installation_code="INSTL-108")
        assert "post_installation_readings" not in row


class TestMissingFieldProvenance:
    def test_all_critical_fields_present_with_confidence_returns_empty(self):
        extracted_fields = {key: {"value": "x", "confidence": 0.9} for key in CRITICAL_PROVENANCE_FIELDS}
        assert missing_field_provenance(extracted_fields) == []

    def test_absent_critical_field_is_reported_missing(self):
        assert "reportNo" in missing_field_provenance({})

    def test_bare_scalar_value_without_confidence_is_reported_missing(self):
        # A value exists, but its confidence was never recorded --
        # "representable by convention" is not the same as "enforced".
        extracted_fields = {"plantEquipNo": "211-P-14B"}
        assert "plantEquipNo" in missing_field_provenance(extracted_fields)

    def test_dict_missing_confidence_key_is_reported_missing(self):
        extracted_fields = {"sealType": {"value": "T15W"}}
        assert "sealType" in missing_field_provenance(extracted_fields)

    def test_complete_field_value_confidence_shape_is_not_reported_missing(self):
        extracted_fields = {"apiPlan": {"value": "22/62", "confidence": 0.97}}
        assert "apiPlan" not in missing_field_provenance(extracted_fields)

    def test_non_critical_fields_are_never_checked(self):
        # "customer"/"address" etc. are not identity-critical -- their
        # absence must not appear in this report.
        assert "customer" not in missing_field_provenance({})
