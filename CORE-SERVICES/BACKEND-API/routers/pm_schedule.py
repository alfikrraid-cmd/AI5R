from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import filter_records_by_asset_scope, is_asset_in_scope
from dependencies import get_current_user, get_pm_schedule_gateway, get_pump_gateway, require_permission
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])

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
    pm_schedule_gateway=Depends(get_pm_schedule_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = pm_schedule_gateway.list_pm_schedules()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        filtered = filter_records_by_asset_scope(response["data"], scope, pump_gateway)
        response = {**response, "data": filtered, "count": len(filtered)}
    return response


@router.get("/api/ltsa/pm-schedules/{code}")
def get_ltsa_pm_schedule(
    code: str,
    pm_schedule_gateway=Depends(get_pm_schedule_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = pm_schedule_gateway.get_pm_schedule(code)
    scope = resolve_area_scope(current_user)
    data = response.get("data") if isinstance(response, dict) else None
    if scope is not None and isinstance(data, dict) and not is_asset_in_scope(data.get("asset_code"), scope, pump_gateway):
        raise HTTPException(status_code=404, detail="PM schedule not found")
    return response
