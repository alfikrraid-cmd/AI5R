from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import filter_records_by_asset_scope, is_asset_in_scope
from dependencies import get_current_user, get_maintenance_history_gateway, get_pump_gateway, require_permission
from models.requests import MaintenanceCreateRequest
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])


@router.post("/maintenance")
def create_maintenance(
    payload: MaintenanceCreateRequest,
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    _write_permission=Depends(require_permission("maintenance.write")),
) -> Payload:
    return maintenance_history_gateway.create_maintenance_history(payload.model_dump())


# Maintenance History Registry API (WO-MH-001) -- same
# MaintenanceHistoryGateway, exposed under the /api/ltsa prefix already used
# by the dashboard's other real LTSA calls (ai5rClient.js). No new gateway,
# service, or repository layer -- mirrors WO-BE-001/WO-PUMP-001's identical
# addition for Work Order/Pump. list_maintenance_history()/
# get_maintenance_history() already existed and were already proven working
# (reused internally by WO-BE-002's Work Order Timeline endpoint and by
# maintenance_intelligence_service.get_pump_history()).


@router.get("/api/ltsa/maintenance-history")
def list_ltsa_maintenance_history(
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = maintenance_history_gateway.list_maintenance_history()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        filtered = filter_records_by_asset_scope(response["data"], scope, pump_gateway)
        response = {**response, "data": filtered, "count": len(filtered)}
    return response


@router.get("/api/ltsa/maintenance-history/{code}")
def get_ltsa_maintenance_history(
    code: str,
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = maintenance_history_gateway.get_maintenance_history(code)
    scope = resolve_area_scope(current_user)
    data = response.get("data") if isinstance(response, dict) else None
    if scope is not None and isinstance(data, dict) and not is_asset_in_scope(data.get("asset_code"), scope, pump_gateway):
        raise HTTPException(status_code=404, detail="Maintenance history record not found")
    return response
