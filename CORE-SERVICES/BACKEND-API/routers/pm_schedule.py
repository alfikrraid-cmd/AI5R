from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from dependencies import get_current_user, get_pm_schedule_repository, require_permission
from models.requests import PMScheduleCreateRequest, PMScheduleUpdateRequest
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])


def _actor_id(user: AuthenticatedIdentity) -> str:
    return user.user_id


@router.post("/api/ltsa/pm-schedules", dependencies=[Depends(require_permission("maintenance.write"))])
def create_pm_schedule(payload: PMScheduleCreateRequest, current_user=Depends(require_permission("maintenance.write")), repository=Depends(get_pm_schedule_repository)) -> Payload:
    created = repository.create(values=payload.model_dump(), actor=_actor_id(current_user))
    if created is None:
        raise HTTPException(status_code=404, detail="Canonical pump not found")
    return {"data": created}


@router.patch("/api/ltsa/pm-schedules/{code}", dependencies=[Depends(require_permission("maintenance.write"))])
def update_pm_schedule(code: str, payload: PMScheduleUpdateRequest, current_user=Depends(require_permission("maintenance.write")), repository=Depends(get_pm_schedule_repository)) -> Payload:
    updated = repository.update(code, values=payload.model_dump(exclude_unset=True), actor=_actor_id(current_user))
    if updated is None:
        raise HTTPException(status_code=404, detail="PM schedule not found")
    return {"data": updated}


@router.delete("/api/ltsa/pm-schedules/{code}", dependencies=[Depends(require_permission("admin.superuser"))])
def delete_pm_schedule(code: str, current_user=Depends(require_permission("admin.superuser")), repository=Depends(get_pm_schedule_repository)) -> Payload:
    deleted = repository.soft_delete(code, actor=_actor_id(current_user))
    if deleted is None:
        raise HTTPException(status_code=404, detail="PM schedule not found")
    return {"data": deleted}

# PM Schedule Registry API (WO-PM-002, per ADR-PM-001) -- same
# PMScheduleGateway built under WO-PM-001, exposed under the /api/ltsa
# prefix already used by the dashboard's other real LTSA calls
# (ai5rClient.js). No new gateway, service, or repository layer -- mirrors
# WO-BE-001/WO-PUMP-001/WO-MH-001's identical addition for Work Order/
# Pump/Maintenance History. Only list/detail are exposed here, matching
# this MWO's scope -- create/update/delete routes were not requested.
#
# MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- pm_schedule carries
# asset_code, never area; scope resolved via pump_gateway.get_pump()
# (API.pump_area_scope), same 1-hop join as every other asset_code
# domain in this closure.


@router.get("/api/ltsa/pm-schedules")
def list_ltsa_pm_schedules(
    pm_schedule_repository=Depends(get_pm_schedule_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return pm_schedule_repository.list_pm_schedules(scope=resolve_area_scope(current_user))


@router.get("/api/ltsa/pm-schedules/{code}")
def get_ltsa_pm_schedule(
    code: str,
    pm_schedule_repository=Depends(get_pm_schedule_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = pm_schedule_repository.get_pm_schedule(code, scope=resolve_area_scope(current_user))
    if response.get("data") is None:
        raise HTTPException(status_code=404, detail="PM schedule not found")
    return response
