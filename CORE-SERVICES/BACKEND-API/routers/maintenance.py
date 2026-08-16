from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_maintenance_history_gateway, require_permission
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
