"""MWO-LTSA-DRAWING-INPUT-R5C -- Engineering Drawing human review
contract: the document_field_extraction.extracted_fields ->
document_field_extraction.reviewed_fields decision layer for
ENGINEERING_DRAWING_CANDIDATE rows.

No SQL, no API, no gateway changes -- pure functions operating on
already-fetched dicts, the SAME "no gateway calls of its own" discipline
installation_review_service.py already establishes for Installation
Report review. Reuses that module's own status vocabulary and
validate_status_transition() verbatim (import, never redefine) --
document_field_extraction.status stays exactly PENDING_REVIEW/REVIEWED/
SAVED/REJECTED for every domain that stages through this one table.

PROMOTION IS OUT OF SCOPE HERE. This module never reads engineering_
drawing/_revision/_attribute et al. and never decides what a reviewed
candidate should become once promoted (Drawing-R5D's own job) -- it only
ever produces the CONTENTS of reviewed_fields plus a
status-transition decision.

RAW AUTHORITY (extracted_fields) is never mutated by anything in this
module -- every function here only ever reads it and returns a NEW
reviewed_fields dict; the caller (engineering_drawing_review_service.py)
is responsible for persisting that returned dict, never extracted_fields.
"""

from __future__ import annotations

from typing import Any, Literal

from .installation_review_service import (  # noqa: F401 -- re-exported for callers
    STATUS_PENDING_REVIEW,
    STATUS_REJECTED,
    STATUS_REVIEWED,
    STATUS_SAVED,
    InvalidReviewTransition,
    validate_status_transition,
)

ReviewAction = Literal["ACCEPT", "CORRECT", "REJECT", "DEFER"]
_VALID_ACTIONS: frozenset[str] = frozenset({"ACCEPT", "CORRECT", "REJECT", "DEFER"})

REVIEW_SCHEMA_VERSION = "drawing-review-v1"

# All 4 identity concepts a reviewer may act on. R5C.1 Section 6's own
# reassessment: completeness ("may this candidate finalize?") requires a
# decision on title+manufacturer only (_MANDATORY_IDENTITY_FIELDS below)
# -- drawing_number and drawing_type may legitimately stay deferred
# forever (R5's own explicit "drawing_number not mandatory" rule,
# extended to drawing_type by the same reasoning: neither is load-bearing
# for identifying WHAT the drawing is or WHO made it, and both are
# genuinely often blank/ambiguous on real drawings per R1's own
# historical evidence). A reviewer may still record a decision on either
# -- it is simply never REQUIRED for completeness.
_IDENTITY_FIELDS: tuple[str, ...] = ("drawing_number", "title", "manufacturer", "drawing_type")
_MANDATORY_IDENTITY_FIELDS: tuple[str, ...] = ("title", "manufacturer")

# Same 5-value vocabulary as migration 038's own
# engineering_drawing_revision_artifact.artifact_class CHECK constraint
# and engineering_drawing_repository.py's own _ARTIFACT_CLASS_VALUES --
# duplicated here (this module has no SQL/canonical-table dependency by
# design) rather than imported from a canonical-table-bound module;
# keep in sync with migration 038 if that vocabulary ever changes.
ARTIFACT_CLASSES: tuple[str, ...] = ("SOURCE_DOCUMENT", "SOURCE_CAD", "DERIVED_CAD", "VIEWER_ASSET", "UNKNOWN")


class InvalidReviewAction(ValueError):
    pass


def _validate_action(action: str) -> None:
    if action not in _VALID_ACTIONS:
        raise InvalidReviewAction(f"invalid review action {action!r}; expected one of {sorted(_VALID_ACTIONS)}")


def apply_identity_field_review(
    reviewed_fields: dict[str, Any],
    *,
    field_name: str,
    action: ReviewAction,
    corrected_raw_value: str | None = None,
) -> dict[str, Any]:
    """Returns a NEW reviewed_fields dict with drawing_identity.<field_name>
    updated per `action`. DEFER is a true no-op (the existing reviewed_fields
    dict is returned completely unchanged, whether or not that field was
    previously reviewed) -- deferring never un-reviews a prior decision.
    """
    _validate_action(action)
    if field_name not in _IDENTITY_FIELDS:
        raise InvalidReviewAction(f"unknown drawing_identity field {field_name!r}; expected one of {_IDENTITY_FIELDS}")
    if action == "DEFER":
        return reviewed_fields

    result = {**reviewed_fields, "drawing_identity": dict(reviewed_fields.get("drawing_identity") or {})}
    if action == "ACCEPT":
        result["drawing_identity"][field_name] = {"review_status": "ACCEPTED"}
    elif action == "REJECT":
        result["drawing_identity"][field_name] = {"review_status": "REJECTED"}
    else:  # CORRECT
        result["drawing_identity"][field_name] = {"review_status": "CORRECTED", "value": corrected_raw_value}
    return result


def apply_revision_review(
    reviewed_fields: dict[str, Any],
    *,
    action: ReviewAction,
    corrected_revision: str | None = None,
    corrected_revision_date: str | None = None,
) -> dict[str, Any]:
    _validate_action(action)
    if action == "DEFER":
        return reviewed_fields

    result = dict(reviewed_fields)
    if action == "ACCEPT":
        result["revision_candidate"] = {"review_status": "ACCEPTED"}
    elif action == "REJECT":
        result["revision_candidate"] = {"review_status": "REJECTED"}
    else:  # CORRECT
        result["revision_candidate"] = {
            "review_status": "CORRECTED",
            "revision": corrected_revision,
            "revision_date": corrected_revision_date,
        }
    return result


def _apply_indexed_review(
    reviewed_fields: dict[str, Any],
    *,
    collection_key: str,
    index: int,
    action: ReviewAction,
    corrected_value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_action(action)
    if index < 0:
        raise InvalidReviewAction(f"index must be >= 0, got {index}")
    if action == "DEFER":
        return reviewed_fields

    result = {**reviewed_fields, collection_key: dict(reviewed_fields.get(collection_key) or {})}
    key = str(index)
    if action == "ACCEPT":
        result[collection_key][key] = {"review_status": "ACCEPTED"}
    elif action == "REJECT":
        result[collection_key][key] = {"review_status": "REJECTED"}
    else:  # CORRECT
        result[collection_key][key] = {"review_status": "CORRECTED", "value": corrected_value or {}}
    return result


def _validate_artifact_class(class_value: str | None, *, param_name: str) -> None:
    if class_value is not None and class_value not in ARTIFACT_CLASSES:
        raise InvalidReviewAction(f"invalid {param_name} {class_value!r}; expected one of {ARTIFACT_CLASSES} or None")


def apply_artifact_review(
    reviewed_fields: dict[str, Any],
    *,
    action: ReviewAction,
    extracted_class: str | None = None,
    corrected_class: str | None = None,
    knowledge_source_id: str | None = None,
) -> dict[str, Any]:
    """R5C.1 Section 3 -- human review authority for artifact
    classification, recorded in reviewed_fields only. NEVER creates a
    canonical engineering_drawing_revision_artifact row (PROMOTION=NO) --
    this is staging-side evidence for Drawing-R5D to later act on.

    File extension/mime type never establishes SOURCE_* on their own --
    this function has no access to either and every class value it
    stores comes only from an explicit `extracted_class`/`corrected_class`
    argument the CALLER supplies (Section 4's own absolute rule).

    ACCEPT: value = extracted_class as supplied by the caller (whatever
    upload-time-declared or otherwise-known candidate exists, if any --
    may legitimately be None, R5B's own extraction adapter never
    proposes an artifact_class). CORRECT: value = corrected_class,
    required, validated against ARTIFACT_CLASSES (UNKNOWN is a valid,
    explicit choice here -- Section 3's own 'UNKNOWN is a VALID RESOLVED
    classification only when explicitly accepted/corrected' rule).
    REJECT: value cleared to None -- the classification is rejected with
    NO replacement recorded by this action alone (a REJECT must be
    followed by a later CORRECT to actually resolve the artifact -- see
    is_artifact_review_complete's own docstring). DEFER: true no-op.

    knowledge_source_id (Section 8) is stored alongside the decision so a
    later reader (R5D) can confirm which uploaded source is being
    classified without a second lookup -- purely descriptive, never a
    canonical artifact_code (never invented here).
    """
    _validate_action(action)
    if action == "DEFER":
        return reviewed_fields

    result = dict(reviewed_fields)
    if action == "ACCEPT":
        _validate_artifact_class(extracted_class, param_name="extracted_class")
        result["artifact"] = {
            "review_status": "ACCEPTED", "value": extracted_class, "knowledge_source_id": knowledge_source_id,
        }
    elif action == "REJECT":
        result["artifact"] = {"review_status": "REJECTED", "value": None, "knowledge_source_id": knowledge_source_id}
    else:  # CORRECT
        if corrected_class is None:
            raise InvalidReviewAction("CORRECT requires an explicit corrected_class")
        _validate_artifact_class(corrected_class, param_name="corrected_class")
        result["artifact"] = {
            "review_status": "CORRECTED", "value": corrected_class, "knowledge_source_id": knowledge_source_id,
        }
    return result


def is_artifact_review_complete(reviewed_fields: dict[str, Any]) -> bool:
    """True only when the artifact has an ACCEPTED or CORRECTED decision
    carrying a valid class value (including the explicit UNKNOWN choice).
    A REJECTED-with-no-replacement artifact is NOT complete -- unlike an
    identity field, an artifact has no legitimate 'genuinely absent'
    state; every artifact needs an actual class for Equipment360 to
    render it correctly later, so REJECT alone always leaves this
    incomplete until a follow-up CORRECT supplies a real class (R5C.1
    Section 9's own explicit rule)."""
    artifact = reviewed_fields.get("artifact") or {}
    return artifact.get("review_status") in ("ACCEPTED", "CORRECTED") and artifact.get("value") in ARTIFACT_CLASSES


def apply_reference_review(reviewed_fields, *, index: int, action: ReviewAction, corrected_value=None) -> dict[str, Any]:
    return _apply_indexed_review(reviewed_fields, collection_key="references", index=index, action=action, corrected_value=corrected_value)


def apply_attribute_review(reviewed_fields, *, index: int, action: ReviewAction, corrected_value=None) -> dict[str, Any]:
    return _apply_indexed_review(reviewed_fields, collection_key="attributes", index=index, action=action, corrected_value=corrected_value)


def apply_bom_review(reviewed_fields, *, index: int, action: ReviewAction, corrected_value=None) -> dict[str, Any]:
    return _apply_indexed_review(reviewed_fields, collection_key="bom_candidates", index=index, action=action, corrected_value=corrected_value)


def is_identity_review_complete(reviewed_fields: dict[str, Any]) -> bool:
    """True once title AND manufacturer both have SOME recorded decision
    (ACCEPTED/CORRECTED/REJECTED) -- R5C.1 Section 6's own reassessment:
    drawing_number/drawing_type are NOT required (see
    _MANDATORY_IDENTITY_FIELDS's own docstring above) -- this is a
    resolved DECISION requirement, never a value requirement. A field
    explicitly reviewed-and-rejected still counts as 'resolved'; a field
    genuinely absent on the source document is correctly ACCEPTED with no
    value at all (R5's own 'unknown remains null' rule) -- never a
    fabricated value."""
    identity = reviewed_fields.get("drawing_identity") or {}
    return all(name in identity for name in _MANDATORY_IDENTITY_FIELDS)


def is_promotion_eligible(reviewed_fields: dict[str, Any]) -> bool:
    """R5C.1 Section 5 -- the CONTENT-level minimum R5 itself established
    for promotion: (A) drawing identity decision resolved AND (B)
    artifact classification decision resolved. Revision/attributes/BOM/
    references never block this -- they may remain fully deferred
    forever. Deliberately named and callable separately from
    can_finalize_review below (Section 5's own 'do not equate them
    accidentally' instruction) even though, today, can_finalize_review
    happens to reuse this exact same content check -- REVIEW_COMPLETE is
    a document_field_extraction.status-transition concern, PROMOTION_
    ELIGIBLE is Drawing-R5D's own separate, later-consulted content
    concern; keeping them as two named functions (not one) means a future
    change to either can decouple them without renaming call sites."""
    return is_identity_review_complete(reviewed_fields) and is_artifact_review_complete(reviewed_fields)


def can_finalize_review(current_status: str, reviewed_fields: dict[str, Any]) -> bool:
    """Whether a PENDING_REVIEW -> REVIEWED transition is currently
    allowed for this candidate: the status machine itself must permit it
    (validate_status_transition) AND the record must be promotion
    eligible (is_promotion_eligible) -- both required."""
    return validate_status_transition(current_status, STATUS_REVIEWED) and is_promotion_eligible(reviewed_fields)


__all__ = [
    "STATUS_PENDING_REVIEW",
    "STATUS_REVIEWED",
    "STATUS_SAVED",
    "STATUS_REJECTED",
    "REVIEW_SCHEMA_VERSION",
    "ARTIFACT_CLASSES",
    "InvalidReviewTransition",
    "InvalidReviewAction",
    "validate_status_transition",
    "apply_identity_field_review",
    "apply_revision_review",
    "apply_artifact_review",
    "apply_reference_review",
    "apply_attribute_review",
    "apply_bom_review",
    "is_identity_review_complete",
    "is_artifact_review_complete",
    "is_promotion_eligible",
    "can_finalize_review",
]
