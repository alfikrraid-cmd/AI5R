from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies import (
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_reading_repository,
    get_condition_monitoring_schedule_gateway,
    require_permission,
)
from models.requests import (
    AdminReturnForCorrectionRequest,
    ConditionMonitoringReadingCreateRequest,
    ConditionMonitoringReadingUpdateRequest,
    TechnicalReviewRequest,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("condition.read"))])

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
    condition_monitoring_schedule_gateway=Depends(get_condition_monitoring_schedule_gateway),
) -> Payload:
    return condition_monitoring_schedule_gateway.list_condition_monitoring_schedules()


@router.get("/api/ltsa/condition-monitoring-schedules/{code}")
def get_ltsa_condition_monitoring_schedule(
    code: str,
    condition_monitoring_schedule_gateway=Depends(get_condition_monitoring_schedule_gateway),
) -> Payload:
    return condition_monitoring_schedule_gateway.get_condition_monitoring_schedule(code)


@router.get("/api/ltsa/condition-monitoring-readings")
def list_ltsa_condition_monitoring_readings(
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
) -> Payload:
    return condition_monitoring_reading_gateway.list_condition_monitoring_readings()


@router.get("/api/ltsa/condition-monitoring-readings/{code}")
def get_ltsa_condition_monitoring_reading(
    code: str,
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
) -> Payload:
    return condition_monitoring_reading_gateway.get_condition_monitoring_reading(code)


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
