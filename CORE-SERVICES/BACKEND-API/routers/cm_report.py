from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_cm_report_gateway, require_permission
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


@router.get("/api/ltsa/cm-reports")
def list_ltsa_cm_reports(cm_report_gateway=Depends(get_cm_report_gateway)) -> Payload:
    return cm_report_gateway.list_cm_reports()


@router.get("/api/ltsa/cm-reports/{code}")
def get_ltsa_cm_report(
    code: str, cm_report_gateway=Depends(get_cm_report_gateway)
) -> Payload:
    return cm_report_gateway.get_cm_report(code)
