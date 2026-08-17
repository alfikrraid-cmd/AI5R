from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_pm_occurrence_gateway, require_permission
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])

# PM Occurrence API (WO-PMOCC-002, per ADR-PM-OCCURRENCE-001) -- same
# PMOccurrenceGateway built under WO-PMOCC-001, exposed under the
# /api/ltsa prefix already used by the dashboard's other real LTSA calls
# (ai5rClient.js). No new gateway, service, or repository layer -- mirrors
# WO-BE-001/WO-PUMP-001/WO-MH-001/WO-PM-002/WO-CM-002/WO-CMON-002's
# identical addition for Work Order/Pump/Maintenance History/PM Schedule/
# CM Report/Condition Monitoring. Only list/detail are exposed here,
# matching this MWO's scope (ADR-PM-OCCURRENCE-001's Required Backend
# Changes item 4) -- create/update/delete routes were not requested, and
# the gateway has no update/delete methods to expose in the first place
# (append-only, per WO-PMOCC-001).
#
# Deliberately independent of routers/cm_report.py and
# routers/condition_monitoring.py -- no shared route prefix, no shared
# gateway, no cross-import, per ADR-PM-OCCURRENCE-001's Reason section.


@router.get("/api/ltsa/pm-occurrences")
def list_ltsa_pm_occurrences(
    pm_occurrence_gateway=Depends(get_pm_occurrence_gateway),
) -> Payload:
    return pm_occurrence_gateway.list_pm_occurrences()


@router.get("/api/ltsa/pm-occurrences/{code}")
def get_ltsa_pm_occurrence(
    code: str, pm_occurrence_gateway=Depends(get_pm_occurrence_gateway)
) -> Payload:
    return pm_occurrence_gateway.get_pm_occurrence(code)
