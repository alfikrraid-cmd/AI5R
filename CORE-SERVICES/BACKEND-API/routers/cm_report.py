from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from dependencies import get_cm_report_repository, get_current_user, require_permission
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("condition.read"))])

# CM Report Registry API (WO-CM-002, per ADR-CM-001) -- same
# CMReportGateway built under WO-CM-001, exposed under the /api/ltsa
# prefix already used by the dashboard's other real LTSA calls
# (ai5rClient.js). No new gateway, service, or repository layer -- mirrors
# WO-BE-001/WO-PUMP-001/WO-MH-001/WO-PM-002's identical addition for Work
# Order/Pump/Maintenance History/PM Schedule. Only list/detail are exposed
# here, matching this MWO's scope (ADR-CM-001's Future MWOs item 2) --
# create/update/delete routes were not requested.
#
# MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- cm_report carries
# asset_code, never area; scope is resolved via pump_gateway.get_pump()
# (API.pump_area_scope), the same 1-hop join routers/work_orders.py's
# get_ltsa_work_order_asset already established.


@router.get("/api/ltsa/cm-reports")
def list_ltsa_cm_reports(
    cm_report_repository=Depends(get_cm_report_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return cm_report_repository.list_cm_reports(scope=resolve_area_scope(current_user))


@router.get("/api/ltsa/cm-reports/{code}")
def get_ltsa_cm_report(
    code: str,
    cm_report_repository=Depends(get_cm_report_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = cm_report_repository.get_cm_report(code, scope=resolve_area_scope(current_user))
    if response.get("data") is None:
        raise HTTPException(status_code=404, detail="CM report not found")
    return response
