from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_product_name, require_permission
from models.responses import Payload
from API.organization_dashboard import get_organization_dashboard as _get_organization_dashboard

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("pump.read"))])


@router.get("/dashboard")
def get_dashboard(product_name: str = Depends(get_product_name)) -> Payload:
    return _get_organization_dashboard(product_name)
