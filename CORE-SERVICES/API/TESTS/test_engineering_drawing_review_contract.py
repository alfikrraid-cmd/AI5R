"""MWO-LTSA-DRAWING-INPUT-R5C / R5C.1 -- pure-function tests for
engineering_drawing_review_contract.py. No DB, no docker -- these are
plain dict-in/dict-out functions, same testing style as any pure module
in this codebase.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
if str(_CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_SERVICES_DIR))

from API.engineering_drawing_review_contract import (  # noqa: E402
    ARTIFACT_CLASSES,
    STATUS_PENDING_REVIEW,
    STATUS_REJECTED,
    STATUS_REVIEWED,
    STATUS_SAVED,
    InvalidReviewAction,
    apply_artifact_review,
    apply_attribute_review,
    apply_bom_review,
    apply_identity_field_review,
    apply_reference_review,
    apply_revision_review,
    can_finalize_review,
    is_artifact_review_complete,
    is_identity_review_complete,
    is_promotion_eligible,
    validate_status_transition,
)

_COMPLETE_IDENTITY = {"drawing_identity": {
    "title": {"review_status": "ACCEPTED"},
    "manufacturer": {"review_status": "ACCEPTED"},
}}
_RESOLVED_ARTIFACT = {"artifact": {"review_status": "ACCEPTED", "value": "SOURCE_DOCUMENT", "knowledge_source_id": "KS-1"}}


def _eligible_reviewed_fields() -> dict:
    return {**_COMPLETE_IDENTITY, **_RESOLVED_ARTIFACT}


# ---- identity field review ----

def test_accept_identity_field():
    result = apply_identity_field_review({}, field_name="manufacturer", action="ACCEPT")
    assert result["drawing_identity"]["manufacturer"] == {"review_status": "ACCEPTED"}


def test_correct_identity_field_preserves_value():
    result = apply_identity_field_review({}, field_name="drawing_number", action="CORRECT", corrected_raw_value="1234-A")
    assert result["drawing_identity"]["drawing_number"] == {"review_status": "CORRECTED", "value": "1234-A"}


def test_reject_identity_field():
    result = apply_identity_field_review({}, field_name="title", action="REJECT")
    assert result["drawing_identity"]["title"] == {"review_status": "REJECTED"}


def test_defer_identity_field_is_true_noop():
    existing = {"drawing_identity": {"manufacturer": {"review_status": "ACCEPTED"}}}
    result = apply_identity_field_review(existing, field_name="drawing_number", action="DEFER")
    assert result == existing  # nothing added, nothing removed


def test_defer_never_unreviews_prior_decision():
    existing = {"drawing_identity": {"manufacturer": {"review_status": "ACCEPTED"}}}
    result = apply_identity_field_review(existing, field_name="manufacturer", action="DEFER")
    assert result["drawing_identity"]["manufacturer"] == {"review_status": "ACCEPTED"}


def test_unknown_identity_field_rejected():
    with pytest.raises(InvalidReviewAction):
        apply_identity_field_review({}, field_name="not_a_real_field", action="ACCEPT")


def test_invalid_action_rejected():
    with pytest.raises(InvalidReviewAction):
        apply_identity_field_review({}, field_name="title", action="MAYBE")


def test_reviewing_one_field_does_not_touch_others():
    existing = {"drawing_identity": {"manufacturer": {"review_status": "ACCEPTED"}}}
    result = apply_identity_field_review(existing, field_name="title", action="ACCEPT")
    assert result["drawing_identity"]["manufacturer"] == {"review_status": "ACCEPTED"}
    assert result["drawing_identity"]["title"] == {"review_status": "ACCEPTED"}


def test_missing_drawing_number_reviewed_as_absent_still_resolves_identity():
    # R5C.1 Section 6: drawing_number not mandatory -- reviewing it as
    # REJECTED (source genuinely has none) resolves it without a value,
    # and identity completeness does not even require this field at all.
    reviewed = apply_identity_field_review({}, field_name="drawing_number", action="REJECT")
    reviewed = apply_identity_field_review(reviewed, field_name="title", action="ACCEPT")
    reviewed = apply_identity_field_review(reviewed, field_name="manufacturer", action="ACCEPT")
    assert is_identity_review_complete(reviewed) is True


# ---- revision review ----

def test_accept_revision():
    result = apply_revision_review({}, action="ACCEPT")
    assert result["revision_candidate"] == {"review_status": "ACCEPTED"}


def test_correct_revision_preserves_values():
    result = apply_revision_review({}, action="CORRECT", corrected_revision="B", corrected_revision_date="2026-06-15")
    assert result["revision_candidate"] == {"review_status": "CORRECTED", "revision": "B", "revision_date": "2026-06-15"}


def test_defer_revision_is_noop():
    assert apply_revision_review({}, action="DEFER") == {}


def test_revision_unknown_does_not_block_eligibility():
    reviewed = _eligible_reviewed_fields()  # revision never touched -- still fully deferred
    assert is_promotion_eligible(reviewed) is True


# ---- artifact classification review ----

def test_artifact_accept_with_extracted_class():
    result = apply_artifact_review({}, action="ACCEPT", extracted_class="SOURCE_DOCUMENT", knowledge_source_id="KS-1")
    assert result["artifact"] == {"review_status": "ACCEPTED", "value": "SOURCE_DOCUMENT", "knowledge_source_id": "KS-1"}


def test_artifact_accept_with_no_extracted_class():
    # ACCEPT is valid even when nothing was extracted (R5B never proposes
    # an artifact_class) -- the caller may still pass None.
    result = apply_artifact_review({}, action="ACCEPT", extracted_class=None, knowledge_source_id="KS-1")
    assert result["artifact"]["value"] is None
    assert result["artifact"]["review_status"] == "ACCEPTED"


def test_artifact_correct_to_explicit_class():
    result = apply_artifact_review({}, action="CORRECT", corrected_class="DERIVED_CAD", knowledge_source_id="KS-1")
    assert result["artifact"] == {"review_status": "CORRECTED", "value": "DERIVED_CAD", "knowledge_source_id": "KS-1"}


def test_artifact_correct_requires_explicit_class():
    with pytest.raises(InvalidReviewAction):
        apply_artifact_review({}, action="CORRECT", corrected_class=None)


def test_artifact_reject_clears_value():
    result = apply_artifact_review({}, action="REJECT", knowledge_source_id="KS-1")
    assert result["artifact"] == {"review_status": "REJECTED", "value": None, "knowledge_source_id": "KS-1"}


def test_artifact_defer_is_noop():
    assert apply_artifact_review({}, action="DEFER") == {}


def test_artifact_invalid_class_rejected():
    with pytest.raises(InvalidReviewAction):
        apply_artifact_review({}, action="CORRECT", corrected_class="NOT_A_REAL_CLASS")


def test_unknown_explicit_acceptance_resolved():
    # UNKNOWN is a VALID resolved classification only when EXPLICITLY
    # chosen by the reviewer (R5C.1 Section 3's own rule).
    result = apply_artifact_review({}, action="CORRECT", corrected_class="UNKNOWN")
    assert result["artifact"]["value"] == "UNKNOWN"
    assert is_artifact_review_complete(result) is True


def test_pdf_does_not_automatically_become_source_document():
    # This function has no mime_type/extension parameter at all -- the
    # only way a class value is ever stored is via an explicit
    # extracted_class/corrected_class argument the CALLER supplies.
    result = apply_artifact_review({}, action="ACCEPT", extracted_class=None)
    assert result["artifact"]["value"] is None  # never silently SOURCE_DOCUMENT


def test_step_label_does_not_automatically_become_source_cad():
    # Same proof from the opposite direction: even if a caller's own
    # (external) label says "STEP", this module accepts only one of the
    # 5 ARTIFACT_CLASSES values verbatim -- it never maps a format label
    # to SOURCE_CAD on its own.
    with pytest.raises(InvalidReviewAction):
        apply_artifact_review({}, action="CORRECT", corrected_class="STEP")


def test_artifact_rejected_without_replacement_incomplete():
    result = apply_artifact_review({}, action="REJECT")
    assert is_artifact_review_complete(result) is False


def test_artifact_rejected_then_corrected_becomes_complete():
    result = apply_artifact_review({}, action="REJECT")
    result = apply_artifact_review(result, action="CORRECT", corrected_class="VIEWER_ASSET")
    assert is_artifact_review_complete(result) is True


def test_all_five_artifact_classes_accepted_by_correct():
    for cls in ARTIFACT_CLASSES:
        result = apply_artifact_review({}, action="CORRECT", corrected_class=cls)
        assert result["artifact"]["value"] == cls


# ---- reference / attribute / BOM indexed review ----

def test_accept_attribute_by_index():
    result = apply_attribute_review({}, index=0, action="ACCEPT")
    assert result["attributes"]["0"] == {"review_status": "ACCEPTED"}


def test_multiple_attribute_indices_independent():
    result = apply_attribute_review({}, index=0, action="ACCEPT")
    result = apply_attribute_review(result, index=1, action="REJECT")
    assert result["attributes"]["0"] == {"review_status": "ACCEPTED"}
    assert result["attributes"]["1"] == {"review_status": "REJECTED"}


def test_correct_attribute_preserves_value():
    result = apply_attribute_review({}, index=2, action="CORRECT", corrected_value={"value_numeric": 4.5, "unit": "in"})
    assert result["attributes"]["2"] == {"review_status": "CORRECTED", "value": {"value_numeric": 4.5, "unit": "in"}}


def test_negative_index_rejected():
    with pytest.raises(InvalidReviewAction):
        apply_attribute_review({}, index=-1, action="ACCEPT")


def test_reference_review_independent_of_attribute_review():
    result = apply_reference_review({}, index=0, action="ACCEPT")
    result = apply_attribute_review(result, index=0, action="REJECT")
    assert result["references"]["0"] == {"review_status": "ACCEPTED"}
    assert result["attributes"]["0"] == {"review_status": "REJECTED"}


def test_bom_review():
    result = apply_bom_review({}, index=3, action="ACCEPT")
    assert result["bom_candidates"]["3"] == {"review_status": "ACCEPTED"}


def test_attributes_deferred_do_not_block_eligibility():
    reviewed = _eligible_reviewed_fields()  # no attribute reviews at all
    assert is_promotion_eligible(reviewed) is True


def test_bom_deferred_does_not_block_eligibility():
    reviewed = _eligible_reviewed_fields()  # no bom reviews at all
    assert is_promotion_eligible(reviewed) is True


# ---- identity-review-complete gate ----

def test_identity_review_incomplete_when_no_fields_reviewed():
    assert is_identity_review_complete({}) is False


def test_identity_review_incomplete_when_partial():
    reviewed = {"drawing_identity": {"manufacturer": {"review_status": "ACCEPTED"}}}
    assert is_identity_review_complete(reviewed) is False


def test_identity_review_complete_with_only_title_and_manufacturer():
    # R5C.1 Section 6: drawing_number/drawing_type are NOT mandatory.
    reviewed = {
        "drawing_identity": {
            "title": {"review_status": "ACCEPTED"},
            "manufacturer": {"review_status": "ACCEPTED"},
        }
    }
    assert is_identity_review_complete(reviewed) is True


def test_identity_review_complete_when_all_four_present():
    reviewed = {
        "drawing_identity": {
            "drawing_number": {"review_status": "REJECTED"},
            "title": {"review_status": "ACCEPTED"},
            "manufacturer": {"review_status": "ACCEPTED"},
            "drawing_type": {"review_status": "REJECTED"},
        }
    }
    assert is_identity_review_complete(reviewed) is True


def test_identity_review_complete_even_with_rejected_fields():
    # A field explicitly reviewed-and-rejected still counts as resolved.
    reviewed = {
        "drawing_identity": {
            "title": {"review_status": "REJECTED"},
            "manufacturer": {"review_status": "REJECTED"},
        }
    }
    assert is_identity_review_complete(reviewed) is True


# ---- status transition reuse ----

def test_status_vocabulary_matches_document_field_extraction():
    assert {STATUS_PENDING_REVIEW, STATUS_REVIEWED, STATUS_SAVED, STATUS_REJECTED} == {
        "PENDING_REVIEW", "REVIEWED", "SAVED", "REJECTED",
    }


def test_validate_status_transition_reused_from_installation_review_service():
    assert validate_status_transition(STATUS_PENDING_REVIEW, STATUS_REVIEWED) is True
    assert validate_status_transition(STATUS_SAVED, STATUS_REVIEWED) is False


# ---- promotion eligibility (content-level, distinct from can_finalize_review) ----

def test_identity_resolved_artifact_resolved_eligible():
    assert is_promotion_eligible(_eligible_reviewed_fields()) is True


def test_identity_resolved_artifact_deferred_blocked():
    assert is_promotion_eligible(dict(_COMPLETE_IDENTITY)) is False


def test_artifact_resolved_identity_unresolved_blocked():
    assert is_promotion_eligible(dict(_RESOLVED_ARTIFACT)) is False


def test_artifact_rejected_without_replacement_blocks_eligibility():
    reviewed = {**_COMPLETE_IDENTITY, "artifact": {"review_status": "REJECTED", "value": None}}
    assert is_promotion_eligible(reviewed) is False


# ---- can_finalize_review ----

def test_cannot_finalize_with_incomplete_identity():
    assert can_finalize_review(STATUS_PENDING_REVIEW, {}) is False


def test_can_finalize_with_complete_identity_and_resolved_artifact():
    assert can_finalize_review(STATUS_PENDING_REVIEW, _eligible_reviewed_fields()) is True


def test_cannot_finalize_with_complete_identity_but_deferred_artifact():
    assert can_finalize_review(STATUS_PENDING_REVIEW, dict(_COMPLETE_IDENTITY)) is False


def test_cannot_finalize_from_terminal_status_even_when_eligible():
    reviewed = _eligible_reviewed_fields()
    assert can_finalize_review(STATUS_SAVED, reviewed) is False
    assert can_finalize_review(STATUS_REJECTED, reviewed) is False
