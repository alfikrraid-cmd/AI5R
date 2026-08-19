from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import filter_records_by_asset_scope, is_asset_in_scope
from dependencies import (
    get_current_user,
    get_pm_occurrence_gateway,
    get_pm_occurrence_repository,
    get_pump_gateway,
    require_permission,
)
from models.requests import (
    AdminReturnForCorrectionRequest,
    PMOccurrenceCreateRequest,
    PMOccurrenceUpdateRequest,
    TechnicalReviewRequest,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])

# PM Occurrence API (WO-PMOCC-002, per ADR-PM-OCCURRENCE-001) -- same
# PMOccurrenceGateway built under WO-PMOCC-001, exposed under the
# /api/ltsa prefix already used by the dashboard's other real LTSA calls
# (ai5rClient.js). No new gateway, service, or repository layer -- mirrors
# WO-BE-001/WO-PUMP-001/WO-MH-001/WO-PM-002/WO-CM-002/WO-CMON-002's
# identical addition for Work Order/Pump/Maintenance History/PM Schedule/
# CM Report/Condition Monitoring. Only list/detail are exposed here,
# matching this MWO's scope (ADR-PM-OCCURRENCE-001's Required Backend
# Changes item 4) -- create/update/delete routes were not requested, and
# the gateway has no update/delete methods to expose in the first place
# (append-only, per WO-PMOCC-001).
#
# Deliberately independent of routers/cm_report.py and
# routers/condition_monitoring.py -- no shared route prefix, no shared
# gateway, no cross-import, per ADR-PM-OCCURRENCE-001's Reason section.


@router.get("/api/ltsa/pm-occurrences")
def list_ltsa_pm_occurrences(
    pm_occurrence_gateway=Depends(get_pm_occurrence_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = pm_occurrence_gateway.list_pm_occurrences()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        filtered = filter_records_by_asset_scope(response["data"], scope, pump_gateway)
        response = {**response, "data": filtered, "count": len(filtered)}
    return response


@router.get("/api/ltsa/pm-occurrences/{code}")
def get_ltsa_pm_occurrence(
    code: str,
    pm_occurrence_gateway=Depends(get_pm_occurrence_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = pm_occurrence_gateway.get_pm_occurrence(code)
    scope = resolve_area_scope(current_user)
    data = response.get("data") if isinstance(response, dict) else None
    if scope is not None and isinstance(data, dict) and not is_asset_in_scope(data.get("asset_code"), scope, pump_gateway):
        raise HTTPException(status_code=404, detail="PM occurrence not found")
    return response


# MWO-LTSA-PM-CM-INTAKE-001 -- the real draft/submit/review write surface
# this router never had. Bypasses PMOccurrenceGateway/n8n entirely (see
# pm_occurrence_repository.py's own header for why) -- the two GET routes
# above are untouched and keep reading the same underlying table this
# repository writes to.
def _actor_id(current_user) -> str:
    return current_user.user_id


@router.post("/api/ltsa/pm-occurrences", dependencies=[Depends(require_permission("maintenance.write"))])
def create_ltsa_pm_occurrence(
    payload: PMOccurrenceCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
) -> Payload:
    created = pm_occurrence_repository.create_draft(
        pm_schedule_code=payload.pm_schedule_code,
        asset_code=payload.asset_code,
        asset_type=payload.asset_type,
        occurrence_date=payload.occurrence_date,
        activities=[entry.model_dump() for entry in payload.activities] if payload.activities else None,
        remarks=payload.remarks,
        created_by=_actor_id(current_user),
    )
    return {"data": created}


@router.patch("/api/ltsa/pm-occurrences/{code}", dependencies=[Depends(require_permission("maintenance.write"))])
def update_ltsa_pm_occurrence_draft(
    code: str,
    payload: PMOccurrenceUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
) -> Payload:
    updated = pm_occurrence_repository.update_draft(
        code,
        occurrence_date=payload.occurrence_date,
        activities=[entry.model_dump() for entry in payload.activities] if payload.activities else None,
        finding=payload.finding,
        preliminary_recommendation=payload.preliminary_recommendation,
        remarks=payload.remarks,
        updated_by=_actor_id(current_user),
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="PM occurrence not found or not editable in its current state")
    return {"data": updated}


@router.post(
    "/api/ltsa/pm-occurrences/{code}/submit", dependencies=[Depends(require_permission("maintenance.write"))]
)
def submit_ltsa_pm_occurrence(
    code: str,
    current_user=Depends(require_permission("maintenance.write")),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
) -> Payload:
    submitted = pm_occurrence_repository.submit(code, submitted_by=_actor_id(current_user))
    if submitted is None:
        raise HTTPException(status_code=409, detail="PM occurrence not found or not submittable in its current state")
    return {"data": submitted}


@router.post(
    "/api/ltsa/pm-occurrences/{code}/admin-review",
    dependencies=[Depends(require_permission("maintenance.admin_review"))],
)
def admin_review_ltsa_pm_occurrence(
    code: str,
    payload: AdminReturnForCorrectionRequest,
    current_user=Depends(require_permission("maintenance.admin_review")),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
) -> Payload:
    # TAP administrative review's only action in this MWO is returning an
    # incomplete SUBMITTED record for correction (Phase 12) -- it never
    # advances a record to FINALIZED itself, that is John Crane's own
    # technical authority (Phase 13), never TAP_ADMIN's.
    returned = pm_occurrence_repository.admin_return_for_correction(
        code, reviewed_by=_actor_id(current_user), return_reason=payload.return_reason
    )
    if returned is None:
        raise HTTPException(status_code=409, detail="PM occurrence not found or not in SUBMITTED state")
    return {"data": returned}


@router.post(
    "/api/ltsa/pm-occurrences/{code}/technical-review",
    dependencies=[Depends(require_permission("maintenance.technical_review"))],
)
def technical_review_ltsa_pm_occurrence(
    code: str,
    payload: TechnicalReviewRequest,
    current_user=Depends(require_permission("maintenance.technical_review")),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
) -> Payload:
    actor = _actor_id(current_user)
    if payload.action == "RETURN":
        result = pm_occurrence_repository.technical_return_for_correction(
            code, technical_reviewed_by=actor, technical_comment=payload.comment
        )
    else:
        outcome = "ACKNOWLEDGED" if payload.action == "ACKNOWLEDGE" else "TECHNICALLY_APPROVED"
        result = pm_occurrence_repository.technical_finalize(
            code,
            technical_reviewed_by=actor,
            technical_outcome=outcome,
            technical_comment=payload.comment,
            technical_recommendation=payload.recommendation,
        )
    if result is None:
        raise HTTPException(status_code=409, detail="PM occurrence not found or not in SUBMITTED state")
    return {"data": result}
