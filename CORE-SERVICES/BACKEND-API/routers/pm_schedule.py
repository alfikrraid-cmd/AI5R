from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_pm_schedule_gateway, require_permission
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])

# PM Schedule Registry API (WO-PM-002, per ADR-PM-001) -- same
# PMScheduleGateway built under WO-PM-001, exposed under the /api/ltsa
# prefix already used by the dashboard's other real LTSA calls
# (ai5rClient.js). No new gateway, service, or repository layer -- mirrors
# WO-BE-001/WO-PUMP-001/WO-MH-001's identical addition for Work Order/
# Pump/Maintenance History. Only list/detail are exposed here, matching
# this MWO's scope -- create/update/delete routes were not requested.


@router.get("/api/ltsa/pm-schedules")
def list_ltsa_pm_schedules(pm_schedule_gateway=Depends(get_pm_schedule_gateway)) -> Payload:
    return pm_schedule_gateway.list_pm_schedules()


@router.get("/api/ltsa/pm-schedules/{code}")
def get_ltsa_pm_schedule(
    code: str, pm_schedule_gateway=Depends(get_pm_schedule_gateway)
) -> Payload:
    return pm_schedule_gateway.get_pm_schedule(code)
