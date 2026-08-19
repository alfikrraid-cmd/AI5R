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
    promote_pm_occurrence_candidate,
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


def _assert_in_scope_or_404(candidate: dict, current_user: AuthenticatedIdentity, pump_gateway) -> None:
    scope = resolve_area_scope(current_user)
    if scope is None:
        return
    asset_code = _candidate_asset_code(candidate)
    if not is_asset_in_scope(asset_code, scope, pump_gateway):
        raise HTTPException(status_code=404, detail="No such candidate")


@router.get("/api/ltsa/historical-review/candidates")
def list_candidates(
    detected_document_type: str | None = None,
    status: str | None = None,
    staging_repository=Depends(get_historical_pm_cmon_staging_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # list_pending() is deliberately status=PENDING_REVIEW only (the
    # repository's own real capability, per its docstring) -- callers
    # asking for a different status get an honest empty list rather than
    # a fabricated result, never a silent fallback to "everything".
    if status not in (None, "PENDING_REVIEW"):
        return {"data": []}
    candidates = staging_repository.list_pending(detected_document_type)
    scope = resolve_area_scope(current_user)
    if scope is not None:
        candidates = [c for c in candidates if is_asset_in_scope(_candidate_asset_code(c), scope, pump_gateway)]
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
    return {"data": candidate}


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

    return {"data": updated}


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
    return {"data": updated}


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

    actor_id = _actor_id(current_user)
    schedule_code = build_unscheduled_reference(candidate.get("source_document_id") or candidate_id)
    try:
        if detected_type == "HISTORICAL_PM_OCCURRENCE_CANDIDATE":
            record = promote_pm_occurrence_candidate(
                candidate, pm_occurrence_repository=pm_occurrence_repository,
                pm_schedule_code=schedule_code, promoted_by=actor_id,
                staging_repository=staging_repository,
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
