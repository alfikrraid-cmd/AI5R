from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import filter_records_by_asset_scope, is_asset_in_scope
from dependencies import get_current_user, get_installation_gateway, get_pump_gateway, require_permission
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("drawing.read"))])

# Installation Report API (MWO-LTSA-060, production persistence path for
# the Installation Workspace created by MWO-LTSA-056) -- reuses
# InstallationGateway unmodified, exposed under the /api/ltsa prefix
# already used by every other LTSA registry endpoint (mirrors
# pm_schedule.py's list/detail pair exactly). List and detail only,
# matching InstallationGateway's own real capability -- create/update/
# delete are out of this MWO's scope.
#
# MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- installation_report's
# own pump-tag field is `plant_equip_no`, not `asset_code` (confirmed
# via EquipmentTimelineService's own field access) -- same 1-hop
# pump_gateway.get_pump() join, different field name.


@router.get("/api/ltsa/installations")
def list_ltsa_installations(
    installation_gateway=Depends(get_installation_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = installation_gateway.list_installations()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        filtered = filter_records_by_asset_scope(response["data"], scope, pump_gateway, asset_field="plant_equip_no")
        response = {**response, "data": filtered, "count": len(filtered)}
    return response


@router.get("/api/ltsa/installations/{installation_code}")
def get_ltsa_installation(
    installation_code: str,
    installation_gateway=Depends(get_installation_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = installation_gateway.get_installation(installation_code)
    scope = resolve_area_scope(current_user)
    data = response.get("data") if isinstance(response, dict) else None
    if scope is not None and isinstance(data, dict) and not is_asset_in_scope(data.get("plant_equip_no"), scope, pump_gateway):
        raise HTTPException(status_code=404, detail="Installation report not found")
    return response
