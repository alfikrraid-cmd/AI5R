"""LTSA_PERTAMINA_RBAC_SCOPE_AND_REQUEST_R2 -- PM / CM / Installation requests.

POST records a request only (ltsa_work_request, migration 055); it never
creates a work order, PM occurrence, CM report or installation record.
PM and CM need maintenance.request, INSTALLATION needs installation.request.
The target asset must be inside the caller's scope, checked server-side with
the same guard the pump read routes use (routers.pumps._guard_tag_in_scope);
an out-of-scope or unknown asset is answered exactly like a missing one.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.work_request_repository import REQUEST_TYPES
from dependencies import (
    get_asset_registry_repository,
    get_current_user,
    get_pump_gateway,
    get_work_request_repository,
    require_permission,
)
from models.requests import WorkRequestCreateRequest
from models.responses import Payload
from routers.pumps import _guard_tag_in_scope

router = APIRouter()

_PERMISSION_BY_TYPE = {
    "PM": "maintenance.request",
    "CM": "maintenance.request",
    "INSTALLATION": "installation.request",
}


@router.post("/api/ltsa/work-requests", status_code=201)
def create_work_request(
    payload: WorkRequestCreateRequest,
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    pump_gateway=Depends(get_pump_gateway),
    asset_registry_repository=Depends(get_asset_registry_repository),
    work_request_repository=Depends(get_work_request_repository),
) -> Payload:
    request_type = (payload.request_type or "").strip().upper()
    if request_type not in REQUEST_TYPES:
        raise HTTPException(status_code=422, detail="request_type must be PM, CM or INSTALLATION")
    permission = _PERMISSION_BY_TYPE[request_type]
    if permission not in current_user.permissions:
        raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
    asset_code = (payload.asset_code or "").strip()
    description = (payload.description or "").strip()
    if not asset_code or not description:
        raise HTTPException(status_code=422, detail="asset_code and description are required")
    _guard_tag_in_scope(asset_code, pump_gateway, current_user, asset_registry_repository)
    if asset_registry_repository.get_asset(asset_code) is None:
        raise HTTPException(status_code=404, detail="Pump not found")
    created = work_request_repository.create(
        request_type=request_type,
        asset_code=asset_code,
        description=description,
        requested_by=current_user.user_id,
    )
    return {"success": True, "data": created}


@router.get("/api/ltsa/work-requests", dependencies=[Depends(require_permission("maintenance.read"))])
def list_work_requests(
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    work_request_repository=Depends(get_work_request_repository),
) -> Payload:
    rows = work_request_repository.list_requests(scope=resolve_area_scope(current_user))
    return {"success": True, "count": len(rows), "data": rows}
