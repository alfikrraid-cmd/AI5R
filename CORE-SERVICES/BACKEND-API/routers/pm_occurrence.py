from __future__ import annotations

import logging

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
    BatchCodesRequest,
    BatchTechnicalReviewRequest,
    PMOccurrenceCreateRequest,
    PMOccurrenceUpdateRequest,
    TechnicalReviewRequest,
)
from models.responses import Payload

logger = logging.getLogger(__name__)

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
    try:
        created = pm_occurrence_repository.create_draft(
            pm_schedule_code=payload.pm_schedule_code,
            asset_code=payload.asset_code,
            asset_type=payload.asset_type,
            occurrence_date=payload.occurrence_date,
            activities=[entry.model_dump() for entry in payload.activities] if payload.activities else None,
            remarks=payload.remarks,
            created_by=_actor_id(current_user),
        )
    except Exception as exc:
        # Diagnostic-only (matches the same privacy/safety standard
        # already established for the WhatsApp CMON writer's own
        # event=whatsapp_cmon_write logging) -- never the request
        # payload, never a raw SQL dump. Re-raises the SAME exception
        # unchanged, so this changes nothing about the response a caller
        # receives; it only makes a write failure diagnosable from logs
        # alone instead of needing a manual DB reproduction.
        first_line = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
        logger.info(
            "event=pm_occurrence_write result=FAILED exception_class=%s sqlstate=%s error_summary=%s",
            type(exc).__name__,
            getattr(exc, "pgcode", None),
            first_line[:200] or None,
        )
        raise
    if created is None:
        raise HTTPException(status_code=404, detail="Canonical pump or PM schedule not found")
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


@router.delete("/api/ltsa/pm-occurrences/{code}", dependencies=[Depends(require_permission("admin.superuser"))])
def delete_ltsa_pm_occurrence(
    code: str,
    current_user=Depends(require_permission("admin.superuser")),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
) -> Payload:
    deleted = pm_occurrence_repository.soft_delete(code, deleted_by=_actor_id(current_user))
    if deleted is None:
        raise HTTPException(status_code=404, detail="PM occurrence not found")
    return {"data": deleted}


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


# MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- thin orchestration only:
# each code below runs through the SAME pm_occurrence_repository.submit()/
# technical_finalize()/technical_return_for_correction() the individual
# routes above already call, one record at a time, in its own independent
# call -- no parallel INSERT/UPDATE path, no new workflow rule, no
# multi-record transaction (matching every other write in this codebase,
# which is already per-record). A record that does not transition is
# never reported as succeeded.
@router.post(
    "/api/ltsa/pm-occurrences/batch-submit", dependencies=[Depends(require_permission("maintenance.write"))]
)
def batch_submit_ltsa_pm_occurrences(
    payload: BatchCodesRequest,
    current_user=Depends(require_permission("maintenance.write")),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
) -> Payload:
    actor = _actor_id(current_user)
    succeeded: list[str] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for code in payload.codes:
        try:
            result = pm_occurrence_repository.submit(code, submitted_by=actor)
        except Exception as exc:  # noqa: BLE001 -- reported per-record, never silently swallowed
            failed.append({"code": code, "reason": str(exc)})
            continue
        if result is None:
            skipped.append({"code": code, "reason": "not found or not in a submittable state"})
        else:
            succeeded.append(code)
    return {"data": {"succeeded": succeeded, "skipped": skipped, "failed": failed}}


@router.post(
    "/api/ltsa/pm-occurrences/batch-technical-review",
    dependencies=[Depends(require_permission("maintenance.technical_review"))],
)
def batch_technical_review_ltsa_pm_occurrences(
    payload: BatchTechnicalReviewRequest,
    current_user=Depends(require_permission("maintenance.technical_review")),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
) -> Payload:
    actor = _actor_id(current_user)
    succeeded: list[str] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for code in payload.codes:
        try:
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
        except Exception as exc:  # noqa: BLE001
            failed.append({"code": code, "reason": str(exc)})
            continue
        if result is None:
            skipped.append({"code": code, "reason": "not found or not in SUBMITTED state"})
        else:
            succeeded.append(code)
    return {"data": {"succeeded": succeeded, "skipped": skipped, "failed": failed}}
