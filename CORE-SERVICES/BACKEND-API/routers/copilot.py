from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_product_name, require_permission
from models.responses import Payload
from API.maintenance_copilot import summarize_maintenance_situation as _summarize_maintenance_situation

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])


@router.get("/copilot/summary")
def copilot_summary(product_name: str = Depends(get_product_name)) -> Payload:
    return _summarize_maintenance_situation(product_name)
