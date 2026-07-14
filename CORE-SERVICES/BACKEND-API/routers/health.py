from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_product_name, get_pump_gateway
from models.responses import HealthResponse
from API.organization_registry import get_organization

router = APIRouter()

API_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
def health(
    product_name: str = Depends(get_product_name),
    pump_gateway=Depends(get_pump_gateway),
) -> HealthResponse:
    try:
        get_organization(product_name)
        organization_status = "OK"
    except Exception:
        organization_status = "UNKNOWN"

    try:
        response = pump_gateway.list_pumps()
        n8n_status = "OK" if response.get("success") else "DOWN"
        database_status = n8n_status
    except Exception:
        n8n_status = "DOWN"
        database_status = "DOWN"

    return HealthResponse(
        status="OK",
        version=API_VERSION,
        organization=organization_status,
        database=database_status,
        n8n=n8n_status,
    )
