from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import (
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_schedule_gateway,
    require_permission,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("condition.read"))])

# Condition Monitoring API (WO-CMON-002, per ADR-CONDITION-MONITORING-001)
# -- same ConditionMonitoringScheduleGateway/ConditionMonitoringReadingGateway
# built under WO-CMON-001, exposed under the /api/ltsa prefix already used
# by the dashboard's other real LTSA calls (ai5rClient.js). No new
# gateway, service, or repository layer -- mirrors WO-BE-001/WO-PUMP-001/
# WO-MH-001/WO-PM-002/WO-CM-002's identical addition for Work Order/Pump/
# Maintenance History/PM Schedule/CM Report. Only list/detail are exposed
# here for both entities, matching this MWO's scope (ADR-CONDITION-
# MONITORING-001's Future MWOs item 2) -- create/update/delete routes
# were not requested, and the Reading gateway has no update/delete
# methods to expose in the first place (append-only, per WO-CMON-001).
#
# Deliberately independent of routers/cm_report.py -- no shared route
# prefix, no shared gateway, no cross-import, per ADR-CONDITION-
# MONITORING-001's Reason section.


@router.get("/api/ltsa/condition-monitoring-schedules")
def list_ltsa_condition_monitoring_schedules(
    condition_monitoring_schedule_gateway=Depends(get_condition_monitoring_schedule_gateway),
) -> Payload:
    return condition_monitoring_schedule_gateway.list_condition_monitoring_schedules()


@router.get("/api/ltsa/condition-monitoring-schedules/{code}")
def get_ltsa_condition_monitoring_schedule(
    code: str,
    condition_monitoring_schedule_gateway=Depends(get_condition_monitoring_schedule_gateway),
) -> Payload:
    return condition_monitoring_schedule_gateway.get_condition_monitoring_schedule(code)


@router.get("/api/ltsa/condition-monitoring-readings")
def list_ltsa_condition_monitoring_readings(
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
) -> Payload:
    return condition_monitoring_reading_gateway.list_condition_monitoring_readings()


@router.get("/api/ltsa/condition-monitoring-readings/{code}")
def get_ltsa_condition_monitoring_reading(
    code: str,
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
) -> Payload:
    return condition_monitoring_reading_gateway.get_condition_monitoring_reading(code)
