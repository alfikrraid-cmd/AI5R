from __future__ import annotations

from fastapi import APIRouter, Depends

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from dependencies import get_current_user, get_product_name, require_permission
from models.responses import Payload
from API.maintenance_copilot import summarize_maintenance_situation as _summarize_maintenance_situation

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])


@router.get("/copilot/summary")
def copilot_summary(
    product_name: str = Depends(get_product_name),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 -- scope threads through
    # to get_maintenance_command_center's own pumps/work_orders/
    # maintenance_history filtering, applied before total_pumps/
    # active_work_orders/completed_today are counted and before
    # recent_work_orders/recent_maintenance are sliced.
    return _summarize_maintenance_situation(product_name, scope=resolve_area_scope(current_user))
