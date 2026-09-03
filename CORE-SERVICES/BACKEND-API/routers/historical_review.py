from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_hoc_pm_cm_upsert import build_unscheduled_reference  # noqa: E402

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.historical_pm_cmon_promotion_service import (
    AlreadyPromotedError,
    PromotionError,
    promote_cmon_reading_candidate,
    promote_pm_occurrence_atomic,
)
from API.historical_bulk_review_service import (
    BatchTooLargeError,
    DuplicateCandidateIdError,
    EmptyBatchError,
    bulk_review_candidates,
    validate_request_shape,
)
from API.historical_pm_cmon_staging_repository import InvalidStatusTransitionError
from API.pump_area_scope import is_asset_in_scope
from dependencies import (
    get_condition_monitoring_reading_repository,
    get_current_user,
    get_historical_pm_cmon_staging_repository,
    get_pm_occurrence_repository,
    get_pump_gateway,
    get_record_change_history_repository,
    require_permission,
)
from models.responses import Payload

# MWO-LTSA-HISTORICAL-REVIEW-UI-001 -- the review/resolve/promote layer
# over the EXISTING July staging pipeline (13a970d/5a5e186). Reuses
# record.edit (SUPERUSER + TAP_ADMIN only, same role set this MWO's own
# policy requires) rather than inventing a second permission for a
# capability that is, at its core, the same "correct a proposed value"
# authority record_edit_service.py already gates -- just applied to a
# not-yet-canonical staging row instead of an already-canonical one.
router = APIRouter(dependencies=[Depends(require_permission("record.edit"))])

_ENTITY_TYPE = "HISTORICAL_STAGING_CANDIDATE"

# Findings are staged but never promoted (see historical_pm_cmon_
# orchestrator.py's own header: a Finding has no reliable per-row date to
# safely auto-attach to one of a pump's multiple CMON readings -- a human
# must attach it manually via the live CMON review UI's own
# update_draft(finding=...), not this promotion path). Disclosed, not
# faked.
_PROMOTABLE_TYPES = {"HISTORICAL_PM_OCCURRENCE_CANDIDATE", "HISTORICAL_CMON_READING_CANDIDATE"}


def _actor_id(current_user: AuthenticatedIdentity) -> str:
    return current_user.user_id


def _candidate_asset_code(candidate: dict) -> str | None:
    return candidate.get("pump_tag_number")


# MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001 -- Core Model. Computed
# from existing columns only (status, pump_tag_number) -- no schema
# change, no stored classification column. A candidate never needs to be
# "complete" to be preserved: INCOMPLETE is a first-class, valid,
# discoverable, later-correctable state, never conflated with INVALID.
#   MATCHED:   pump_tag_number resolved -- canonical pump relation known.
#   INCOMPLETE: a valid historical observation whose pump relation (or
#               other canonical value) is not yet resolved. Still
#               promotable once completed; never promotable as-is
#               (promote_*_candidate's own existing pump_tag_number
#               check already enforces this, unchanged).
#   INVALID:   REJECTED -- a human explicitly decided this candidate is
#               not a valid historical observation at all. Never
#               promotable (same existing REVIEWED-only gate).
def classify_candidate(candidate: dict) -> str:
    if candidate.get("status") == "REJECTED":
        return "INVALID"
    if candidate.get("pump_tag_number"):
        return "MATCHED"
    return "INCOMPLETE"


_RECOVERY_ELIGIBLE_DOMAIN = "HISTORICAL_PM_OCCURRENCE_CANDIDATE"
_RECOVERY_ELIGIBLE_STATUS = "PENDING_REVIEW"


# MWO-LTSA-EXACT-540-RECOVERY-UI-001 -- server-derived, not frontend-
# reimplemented: the ONLY place that decides "is this candidate part of
# the selectively staged deterministic recovery batch" is here, reusing
# the exact same fields historical_bulk_review_service.py's own
# eligibility check already reads (detected_document_type, status,
# extracted_fields->>'candidate_identity_v2'). candidate_identity_v2 is
# written ONLY by historical_selective_staging_service.stage_verified_
# batch() (verified against production: every row carrying it belongs to
# the single 540-candidate recovery manifest, zero exceptions) -- no
# second table, no schema change, no new column.
def _is_recovery_batch_eligible(candidate: dict) -> bool:
    if candidate.get("detected_document_type") != _RECOVERY_ELIGIBLE_DOMAIN:
        return False
    if candidate.get("status") != _RECOVERY_ELIGIBLE_STATUS:
        return False
    fields = candidate.get("extracted_fields") or {}
    return bool(fields.get("candidate_identity_v2"))


def _with_classification(candidate: dict) -> dict:
    return {
        **candidate,
        "classification": classify_candidate(candidate),
        "recovery_batch_eligible": _is_recovery_batch_eligible(candidate),
    }


def _assert_in_scope_or_404(candidate: dict, current_user: AuthenticatedIdentity, pump_gateway) -> None:
    scope = resolve_area_scope(current_user)
    if scope is None:
        return
    asset_code = _candidate_asset_code(candidate)
    if not is_asset_in_scope(asset_code, scope, pump_gateway):
        raise HTTPException(status_code=404, detail="No such candidate")


_LISTABLE_STATUSES = {"PENDING_REVIEW", "REVIEWED", "REJECTED", "SAVED"}


@router.get("/api/ltsa/historical-review/candidates")
def list_candidates(
    detected_document_type: str | None = None,
    status: str | None = None,
    staging_repository=Depends(get_historical_pm_cmon_staging_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001 -- widened from
    # PENDING_REVIEW-only so an INCOMPLETE observation that has already
    # been reviewed (status REVIEWED, pump_tag_number still NULL) stays
    # discoverable after a page reload, per this MWO's own "must remain
    # discoverable in Historical Review" rule. An unrecognized status
    # still gets an honest empty list, never a fabricated result.
    effective_status = status or "PENDING_REVIEW"
    if effective_status not in _LISTABLE_STATUSES:
        return {"data": [], "count": 0}
    candidates = staging_repository.list_by_status(effective_status, detected_document_type)
    scope = resolve_area_scope(current_user)
    if scope is not None:
        candidates = [c for c in candidates if is_asset_in_scope(_candidate_asset_code(c), scope, pump_gateway)]
    candidates = [_with_classification(c) for c in candidates]
    return {"data": candidates, "count": len(candidates)}


@router.get("/api/ltsa/historical-review/candidates/{candidate_id}")
def get_candidate(
    candidate_id: str,
    staging_repository=Depends(get_historical_pm_cmon_staging_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    candidate = staging_repository.find_by_id(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="No such candidate")
    _assert_in_scope_or_404(candidate, current_user, pump_gateway)
    return {"data": _with_classification(candidate)}


class ReviewRequest(BaseModel):
    # None = confirm as-extracted (no field-level correction). A non-None
    # dict differing from extracted_fields, or a pump_tag_number differing
    # from the candidate's current one, is a correction -- reason becomes
    # required for those, never for a plain confirm.
    reviewed_fields: dict[str, Any] | None = None
    pump_tag_number: str | None = None
    reason: str | None = None


def _diff_fields(old: dict, new: dict) -> list[tuple[str, Any, Any]]:
    changes = []
    for key in new:
        old_value = old.get(key)
        new_value = new[key]
        if old_value != new_value:
            changes.append((key, old_value, new_value))
    return changes


@router.post("/api/ltsa/historical-review/candidates/{candidate_id}/review")
def review_candidate(
    candidate_id: str,
    payload: ReviewRequest,
    staging_repository=Depends(get_historical_pm_cmon_staging_repository),
    history_repository=Depends(get_record_change_history_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    candidate = staging_repository.find_by_id(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="No such candidate")
    _assert_in_scope_or_404(candidate, current_user, pump_gateway)

    extracted_fields = candidate.get("extracted_fields") or {}
    effective_fields = payload.reviewed_fields if payload.reviewed_fields is not None else extracted_fields
    field_changes = _diff_fields(extracted_fields, effective_fields)
    pump_changed = (
        payload.pump_tag_number is not None and payload.pump_tag_number != candidate.get("pump_tag_number")
    )
    is_correction = bool(field_changes) or pump_changed

    if is_correction and not (payload.reason and payload.reason.strip()):
        raise HTTPException(status_code=422, detail="reason is required for a manual correction/resolution")

    actor_id = _actor_id(current_user)
    try:
        updated = staging_repository.apply_review(
            candidate_id,
            reviewed_fields=effective_fields,
            reviewed_by=actor_id,
            pump_tag_number=payload.pump_tag_number,
        )
    except InvalidStatusTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if updated is None:
        raise HTTPException(status_code=404, detail="No such candidate")

    # Reuses the SAME record_change_history ledger ff4b938 built --
    # never a second audit table -- one row per genuinely-changed field,
    # entity_type distinguishes a staging correction from a canonical
    # Edit Value correction without needing a separate mechanism.
    if is_correction:
        for field_name, old_value, new_value in field_changes:
            history_repository.append(
                entity_type=_ENTITY_TYPE, entity_id=candidate_id, field_name=field_name,
                old_value=None if old_value is None else str(old_value),
                new_value=None if new_value is None else str(new_value),
                changed_by=actor_id, reason=payload.reason,
                source_reference=f"document_field_extraction:{candidate_id}",
            )
        if pump_changed:
            history_repository.append(
                entity_type=_ENTITY_TYPE, entity_id=candidate_id, field_name="pump_tag_number",
                old_value=candidate.get("pump_tag_number"), new_value=payload.pump_tag_number,
                changed_by=actor_id, reason=payload.reason,
                source_reference=f"document_field_extraction:{candidate_id}",
            )

    return {"data": _with_classification(updated)}


class RejectRequest(BaseModel):
    reason: str


@router.post("/api/ltsa/historical-review/candidates/{candidate_id}/reject")
def reject_candidate(
    candidate_id: str,
    payload: RejectRequest,
    staging_repository=Depends(get_historical_pm_cmon_staging_repository),
    history_repository=Depends(get_record_change_history_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="reason is required to reject a candidate")
    candidate = staging_repository.find_by_id(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="No such candidate")
    _assert_in_scope_or_404(candidate, current_user, pump_gateway)

    actor_id = _actor_id(current_user)
    try:
        updated = staging_repository.reject(candidate_id, reviewed_by=actor_id)
    except InvalidStatusTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if updated is None:
        raise HTTPException(status_code=404, detail="No such candidate")

    history_repository.append(
        entity_type=_ENTITY_TYPE, entity_id=candidate_id, field_name="status",
        old_value=candidate.get("status"), new_value="REJECTED",
        changed_by=actor_id, reason=payload.reason,
        source_reference=f"document_field_extraction:{candidate_id}",
    )
    return {"data": _with_classification(updated)}


@router.post("/api/ltsa/historical-review/candidates/{candidate_id}/promote")
def promote_candidate(
    candidate_id: str,
    staging_repository=Depends(get_historical_pm_cmon_staging_repository),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
    cmon_repository=Depends(get_condition_monitoring_reading_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    candidate = staging_repository.find_by_id(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="No such candidate")
    _assert_in_scope_or_404(candidate, current_user, pump_gateway)

    detected_type = candidate.get("detected_document_type")
    if detected_type not in _PROMOTABLE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"{detected_type!r} is not a promotable candidate type",
        )

    # MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001 -- explicit,
    # readable promotion-safety gate matching the Core Model directly:
    # INVALID never promotes (redundant with, but clearer than, the
    # underlying REVIEWED-only check every PromotionError already
    # enforces); INCOMPLETE never promotes as-is -- the existing
    # pump_tag_number check in promote_*_candidate() is the real
    # enforcement, this only gives a classification-aware error message.
    classification = classify_candidate(candidate)
    if classification == "INVALID":
        raise HTTPException(status_code=422, detail="candidate is INVALID (rejected) -- cannot promote")
    if classification == "INCOMPLETE":
        raise HTTPException(
            status_code=422,
            detail="candidate is INCOMPLETE (pump relation unresolved) -- resolve the pump match before promoting",
        )

    actor_id = _actor_id(current_user)
    schedule_code = build_unscheduled_reference(candidate.get("source_document_id") or candidate_id)
    try:
        if detected_type == "HISTORICAL_PM_OCCURRENCE_CANDIDATE":
            record = promote_pm_occurrence_atomic(
                candidate_id, pm_occurrence_repository=pm_occurrence_repository,
                pm_schedule_code=schedule_code, promoted_by=actor_id,
            )
        else:
            record = promote_cmon_reading_candidate(
                candidate, cmon_repository=cmon_repository,
                condition_monitoring_schedule_code=schedule_code, promoted_by=actor_id,
                staging_repository=staging_repository,
            )
    except AlreadyPromotedError:
        raise HTTPException(status_code=409, detail="candidate already promoted (SAVED) -- cannot promote again")
    except PromotionError as error:
        raise HTTPException(status_code=422, detail=str(error))

    return {"data": record}


class BulkReviewRequest(BaseModel):
    # Explicit id list only -- this endpoint never rediscovers or
    # reclassifies a batch itself, matching historical_selective_
    # staging_service's own "caller supplies the exact manifest" rule.
    candidate_ids: list[str]


# MWO-LTSA-BULK-HISTORICAL-REVIEW-001 -- a second, narrower review path
# for a human reviewer who has already verified an entire recovery batch
# out-of-band and needs to confirm it in bulk. Reuses this router's own
# record.edit gate, get_current_user for the reviewer identity (never
# client-supplied, same as review_candidate's actor_id), and
# _assert_in_scope_or_404 per candidate (never a partial-scope leak).
# Only ever confirms-as-extracted: no reviewed_fields/pump_tag_number/
# reason in the request body at all, so no correction is possible here --
# a correction still requires the existing single-candidate /review
# action. Promotion remains a fully separate action (per-candidate
# /promote, unchanged) -- this endpoint never writes pm_occurrence.
@router.post("/api/ltsa/historical-review/candidates/bulk-review")
def bulk_review_candidates_endpoint(
    payload: BulkReviewRequest,
    staging_repository=Depends(get_historical_pm_cmon_staging_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # Cheap request-shape check first (no repository access) -- a
    # malformed request (empty/oversized/duplicate ids) is rejected
    # before spending one find_by_id + scope check per id.
    try:
        validate_request_shape(payload.candidate_ids)
    except (EmptyBatchError, BatchTooLargeError, DuplicateCandidateIdError) as error:
        raise HTTPException(status_code=422, detail=str(error))

    for candidate_id in payload.candidate_ids:
        candidate = staging_repository.find_by_id(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail=f"No such candidate: {candidate_id}")
        _assert_in_scope_or_404(candidate, current_user, pump_gateway)

    actor_id = _actor_id(current_user)
    result = bulk_review_candidates(staging_repository, payload.candidate_ids, reviewed_by=actor_id)

    if result["status"] == "REJECTED_PRECHECK_FAILED":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "one or more candidates are not eligible for bulk review (must be PENDING_REVIEW + PM)",
                "counts": result["precheck"]["counts"],
            },
        )
    if result["status"] == "REJECTED_ATOMIC_TRANSACTION_FAILED":
        raise HTTPException(status_code=409, detail=result.get("error", "bulk review transaction failed"))

    return {
        "data": {
            "reviewed_count": len(result["reviewed"]),
            "candidate_ids": [r["document_field_extraction_id"] for r in result["reviewed"]],
        }
    }
