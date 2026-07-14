from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_product_name
from models.responses import Payload
from API.organization_dashboard import get_organization_dashboard as _get_organization_dashboard

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(product_name: str = Depends(get_product_name)) -> Payload:
    return _get_organization_dashboard(product_name)
