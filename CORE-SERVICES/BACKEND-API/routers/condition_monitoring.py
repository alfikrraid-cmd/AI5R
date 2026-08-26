from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import filter_records_by_asset_scope, is_asset_in_scope
from dependencies import (
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_reading_repository,
    get_condition_monitoring_schedule_repository,
    get_current_user,
    get_pump_gateway,
    require_permission,
)
from models.requests import (
    AdminReturnForCorrectionRequest,
    BatchCodesRequest,
    BatchTechnicalReviewRequest,
    ConditionMonitoringReadingCreateRequest,
    ConditionMonitoringReadingUpdateRequest,
    TechnicalReviewRequest,
    ConditionMonitoringScheduleCreateRequest,
    ConditionMonitoringScheduleUpdateRequest,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("condition.read"))])


@router.post("/api/ltsa/condition-monitoring-schedules", dependencies=[Depends(require_permission("maintenance.write"))])
def create_condition_monitoring_schedule(payload: ConditionMonitoringScheduleCreateRequest, current_user=Depends(require_permission("maintenance.write")), repository=Depends(get_condition_monitoring_schedule_repository)) -> Payload:
    created = repository.create(values=payload.model_dump(), actor=current_user.user_id)
    if created is None:
        raise HTTPException(status_code=404, detail="Canonical pump not found")
    return {"data": created}


@router.patch("/api/ltsa/condition-monitoring-schedules/{code}", dependencies=[Depends(require_permission("maintenance.write"))])
def update_condition_monitoring_schedule(code: str, payload: ConditionMonitoringScheduleUpdateRequest, current_user=Depends(require_permission("maintenance.write")), repository=Depends(get_condition_monitoring_schedule_repository)) -> Payload:
    updated = repository.update(code, values=payload.model_dump(exclude_unset=True), actor=current_user.user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring schedule not found")
    return {"data": updated}


@router.delete("/api/ltsa/condition-monitoring-schedules/{code}", dependencies=[Depends(require_permission("admin.superuser"))])
def delete_condition_monitoring_schedule(code: str, current_user=Depends(require_permission("admin.superuser")), repository=Depends(get_condition_monitoring_schedule_repository)) -> Payload:
    deleted = repository.soft_delete(code, actor=current_user.user_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring schedule not found")
    return {"data": deleted}

# Condition Monitoring API (WO-CMON-002, per ADR-CONDITION-MONITORING-001)
# -- same ConditionMonitoringScheduleGateway/ConditionMonitoringReadingGateway
# built under WO-CMON-001, exposed under the /api/ltsa prefix already used
# by the dashboard's other real LTSA calls (ai5rClient.js). No new
# gateway, service, or repository layer -- mirrors WO-BE-001/WO-PUMP-001/
# WO-MH-001/WO-PM-002/WO-CM-002's identical addition for Work Order/Pump/
# Maintenance History/PM Schedule/CM Report. Only list/detail are exposed
# here for both entities, matching this MWO's scope (ADR-CONDITION-
# MONITORING-001's Future MWOs item 2) -- create/update/delete routes
# were not requested, and the Reading gateway has no update/delete
# methods to expose in the first place (append-only, per WO-CMON-001).
#
# Deliberately independent of routers/cm_report.py -- no shared route
# prefix, no shared gateway, no cross-import, per ADR-CONDITION-
# MONITORING-001's Reason section.


@router.get("/api/ltsa/condition-monitoring-schedules")
def list_ltsa_condition_monitoring_schedules(
    condition_monitoring_schedule_repository=Depends(get_condition_monitoring_schedule_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return condition_monitoring_schedule_repository.list_condition_monitoring_schedules(
        scope=resolve_area_scope(current_user)
    )


@router.get("/api/ltsa/condition-monitoring-schedules/{code}")
def get_ltsa_condition_monitoring_schedule(
    code: str,
    condition_monitoring_schedule_repository=Depends(get_condition_monitoring_schedule_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = condition_monitoring_schedule_repository.get_condition_monitoring_schedule(
        code, scope=resolve_area_scope(current_user)
    )
    if response.get("data") is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring schedule not found")
    return response


@router.get("/api/ltsa/condition-monitoring-readings")
def list_ltsa_condition_monitoring_readings(
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return condition_monitoring_reading_repository.list_all(
        scope=resolve_area_scope(current_user), limit=limit, offset=offset
    )


@router.get("/api/ltsa/condition-monitoring-readings/{code}")
def get_ltsa_condition_monitoring_reading(
    code: str,
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    data = condition_monitoring_reading_repository.find_by_code(code)
    scope = resolve_area_scope(current_user)
    if data is None or (scope is not None and not is_asset_in_scope(data.get("asset_code"), scope, pump_gateway)):
        raise HTTPException(status_code=404, detail="Condition Monitoring reading not found")
    return {"success": True, "message": "found", "data": data}


# MWO-LTSA-PM-CM-INTAKE-001 -- real draft/submit/review write surface for
# Condition Monitoring Reading. Bypasses ConditionMonitoringReadingGateway/
# n8n entirely (append-only per WO-CMON-001, same reasoning as
# pm_occurrence's own write routes) -- the two GET routes above are
# untouched. Deliberately gated on maintenance.write/maintenance.
# admin_review/maintenance.technical_review, the same permissions PM
# Occurrence uses, not a new condition.write string -- every role that
# needs to reach this domain already holds both maintenance.* and
# condition.read together (confirmed by reading the real ROLE_PERMISSIONS
# matrix before choosing this), so reusing them is the smallest correct
# capability, not a new one invented to fit this router.
def _actor_id(current_user) -> str:
    return current_user.user_id


@router.post(
    "/api/ltsa/condition-monitoring-readings",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_ltsa_condition_monitoring_reading(
    payload: ConditionMonitoringReadingCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    created = condition_monitoring_reading_repository.create_draft(
        condition_monitoring_schedule_code=payload.condition_monitoring_schedule_code,
        asset_code=payload.asset_code,
        asset_type=payload.asset_type,
        reading_date=payload.reading_date,
        measurements=payload.measurements.model_dump(),
        created_by=_actor_id(current_user),
    )
    if created is None:
        raise HTTPException(status_code=404, detail="Canonical pump or Condition Monitoring schedule not found")
    return {"data": created}


@router.patch(
    "/api/ltsa/condition-monitoring-readings/{code}",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def update_ltsa_condition_monitoring_reading_draft(
    code: str,
    payload: ConditionMonitoringReadingUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    updated = condition_monitoring_reading_repository.update_draft(
        code,
        reading_date=payload.reading_date,
        measurements=payload.measurements.model_dump(),
        finding=payload.finding,
        updated_by=_actor_id(current_user),
    )
    if updated is None:
        raise HTTPException(
            status_code=409, detail="Condition Monitoring reading not found or not editable in its current state"
        )
    return {"data": updated}


@router.delete(
    "/api/ltsa/condition-monitoring-readings/{code}",
    dependencies=[Depends(require_permission("admin.superuser"))],
)
def delete_ltsa_condition_monitoring_reading(
    code: str,
    current_user=Depends(require_permission("admin.superuser")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    deleted = condition_monitoring_reading_repository.soft_delete(code, deleted_by=_actor_id(current_user))
    if deleted is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring reading not found")
    return {"data": deleted}


@router.post(
    "/api/ltsa/condition-monitoring-readings/{code}/submit",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def submit_ltsa_condition_monitoring_reading(
    code: str,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    submitted = condition_monitoring_reading_repository.submit(code, submitted_by=_actor_id(current_user))
    if submitted is None:
        raise HTTPException(
            status_code=409, detail="Condition Monitoring reading not found or not submittable in its current state"
        )
    return {"data": submitted}


@router.post(
    "/api/ltsa/condition-monitoring-readings/{code}/admin-review",
    dependencies=[Depends(require_permission("maintenance.admin_review"))],
)
def admin_review_ltsa_condition_monitoring_reading(
    code: str,
    payload: AdminReturnForCorrectionRequest,
    current_user=Depends(require_permission("maintenance.admin_review")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    returned = condition_monitoring_reading_repository.admin_return_for_correction(
        code, reviewed_by=_actor_id(current_user), return_reason=payload.return_reason
    )
    if returned is None:
        raise HTTPException(status_code=409, detail="Condition Monitoring reading not found or not in SUBMITTED state")
    return {"data": returned}


@router.post(
    "/api/ltsa/condition-monitoring-readings/{code}/technical-review",
    dependencies=[Depends(require_permission("maintenance.technical_review"))],
)
def technical_review_ltsa_condition_monitoring_reading(
    code: str,
    payload: TechnicalReviewRequest,
    current_user=Depends(require_permission("maintenance.technical_review")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    actor = _actor_id(current_user)
    if payload.action == "RETURN":
        result = condition_monitoring_reading_repository.technical_return_for_correction(
            code, technical_reviewed_by=actor, technical_comment=payload.comment
        )
    else:
        outcome = "ACKNOWLEDGED" if payload.action == "ACKNOWLEDGE" else "TECHNICALLY_APPROVED"
        result = condition_monitoring_reading_repository.technical_finalize(
            code,
            technical_reviewed_by=actor,
            technical_outcome=outcome,
            technical_comment=payload.comment,
            technical_recommendation=payload.recommendation,
        )
    if result is None:
        raise HTTPException(status_code=409, detail="Condition Monitoring reading not found or not in SUBMITTED state")
    return {"data": result}


# MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- see pm_occurrence.py's
# own identical batch routes for the full reasoning: thin per-record
# orchestration around the SAME condition_monitoring_reading_repository
# methods the individual routes above already call.
@router.post(
    "/api/ltsa/condition-monitoring-readings/batch-submit",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def batch_submit_ltsa_condition_monitoring_readings(
    payload: BatchCodesRequest,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    actor = _actor_id(current_user)
    succeeded: list[str] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for code in payload.codes:
        try:
            result = condition_monitoring_reading_repository.submit(code, submitted_by=actor)
        except Exception as exc:  # noqa: BLE001
            failed.append({"code": code, "reason": str(exc)})
            continue
        if result is None:
            skipped.append({"code": code, "reason": "not found or not in a submittable state"})
        else:
            succeeded.append(code)
    return {"data": {"succeeded": succeeded, "skipped": skipped, "failed": failed}}


@router.post(
    "/api/ltsa/condition-monitoring-readings/batch-technical-review",
    dependencies=[Depends(require_permission("maintenance.technical_review"))],
)
def batch_technical_review_ltsa_condition_monitoring_readings(
    payload: BatchTechnicalReviewRequest,
    current_user=Depends(require_permission("maintenance.technical_review")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    actor = _actor_id(current_user)
    succeeded: list[str] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for code in payload.codes:
        try:
            if payload.action == "RETURN":
                result = condition_monitoring_reading_repository.technical_return_for_correction(
                    code, technical_reviewed_by=actor, technical_comment=payload.comment
                )
            else:
                outcome = "ACKNOWLEDGED" if payload.action == "ACKNOWLEDGE" else "TECHNICALLY_APPROVED"
                result = condition_monitoring_reading_repository.technical_finalize(
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
