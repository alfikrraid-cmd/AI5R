from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_maintenance_history_gateway
from models.requests import MaintenanceCreateRequest
from models.responses import Payload

router = APIRouter()


@router.post("/maintenance")
def create_maintenance(
    payload: MaintenanceCreateRequest,
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
) -> Payload:
    return maintenance_history_gateway.create_maintenance_history(payload.model_dump())
