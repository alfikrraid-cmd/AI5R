from __future__ import annotations

import dataclasses

from fastapi import APIRouter, Depends

from API.maintenance_intelligence_service import (
    get_active_work_orders,
    get_pump_condition_monitoring_flag,
    get_pump_last_cm,
    get_pump_last_pm,
    get_pump_spare_parts,
)
from dependencies import (
    get_cm_report_gateway,
    get_condition_monitoring_reading_gateway,
    get_engineering_context_engine,
    get_equipment_timeline_service,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_pm_occurrence_gateway,
    get_pump_gateway,
    get_seal_gateway,
    get_seal_pump_compatibility_gateway,
    get_seal_stock_gateway,
    get_work_order_gateway,
)
from models.responses import Payload

router = APIRouter()


@router.get("/pumps")
def list_pumps(pump_gateway=Depends(get_pump_gateway)) -> Payload:
    return pump_gateway.list_pumps()


@router.get("/pumps/{tag}")
def get_pump(tag: str, pump_gateway=Depends(get_pump_gateway)) -> Payload:
    return pump_gateway.get_pump(tag)


# Pump Registry API (WO-PUMP-001) -- same PumpGateway, exposed under the
# /api/ltsa prefix already used by the dashboard's other real LTSA calls
# (ai5rClient.js). No new gateway, service, or repository layer -- mirrors
# WO-BE-001's identical addition for Work Order.


@router.get("/api/ltsa/pumps")
def list_ltsa_pumps(pump_gateway=Depends(get_pump_gateway)) -> Payload:
    return pump_gateway.list_pumps()


@router.get("/api/ltsa/pumps/{tag}")
def get_ltsa_pump(tag: str, pump_gateway=Depends(get_pump_gateway)) -> Payload:
    return pump_gateway.get_pump(tag)


# Open Work Orders / openWO (WO-PUMP-003) -- per ADR-PUMP-001, openWO is
# Derived, owned by Work Order, not a ltsa_pumps column. Delegates entirely
# to the existing maintenance_intelligence_service.get_active_work_orders(),
# which already filters WorkOrderGateway.list_work_orders() by asset_code
# and not closed_at -- no new gateway, no duplicated filter logic.


@router.get("/api/ltsa/pumps/{tag}/workorders")
def get_ltsa_pump_open_work_orders(
    tag: str,
    work_order_gateway=Depends(get_work_order_gateway),
) -> Payload:
    result = get_active_work_orders(tag, work_order_gateway=work_order_gateway)
    work_orders = result.get("work_orders") or []

    return {
        "success": result.get("success", False),
        "tag_number": tag,
        "openWO": len(work_orders),
        "data": work_orders,
    }


# Last PM / lastPM (WO-PUMP-004, per ADR-PUMP-002; updated under
# MWO-MAINTINT-001 per ADR-PM-OCCURRENCE-001) -- lastPM is Derived,
# considering both a Work-Order-linked maintenance_history record
# (ADR-PUMP-002's original source, still valid) and the canonical
# pm_occurrence log (ADR-PM-OCCURRENCE-001), returning whichever is more
# recent. Delegates entirely to the existing
# maintenance_intelligence_service.get_pump_last_pm(), unmodified beyond
# its own MWO-MAINTINT-001 update -- no new gateway, no duplicated logic.


@router.get("/api/ltsa/pumps/{tag}/last-pm")
def get_ltsa_pump_last_pm(
    tag: str,
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    work_order_gateway=Depends(get_work_order_gateway),
    pm_occurrence_gateway=Depends(get_pm_occurrence_gateway),
) -> Payload:
    return get_pump_last_pm(
        tag,
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )


# Last CM / lastCM and Condition Monitoring Flag (WO-ASSET360-001, per
# ADR-ASSET360-001) -- both Derived, both delegate entirely to the
# existing maintenance_intelligence_service functions -- no new gateway,
# no duplicated logic.


@router.get("/api/ltsa/pumps/{tag}/last-cm")
def get_ltsa_pump_last_cm(
    tag: str,
    cm_report_gateway=Depends(get_cm_report_gateway),
) -> Payload:
    return get_pump_last_cm(tag, cm_report_gateway=cm_report_gateway)


@router.get("/api/ltsa/pumps/{tag}/condition-monitoring-flag")
def get_ltsa_pump_condition_monitoring_flag(
    tag: str,
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
) -> Payload:
    return get_pump_condition_monitoring_flag(
        tag, condition_monitoring_reading_gateway=condition_monitoring_reading_gateway
    )


# Spare Parts / Inventory Context Experience (MWO-INV-CTX-001) -- engineering
# context only, not warehouse management: which seals are compatible with
# this pump and their current stock, read-only. Delegates entirely to the
# existing maintenance_intelligence_service.get_pump_spare_parts(), which
# joins the Seal domain's existing seal_pump_compatibility/seal_stock/
# seal_registry data (MWO-LTSA-030, previously schema-only) -- no new
# gateway logic here, no persistence, no create/update/delete route.


@router.get("/api/ltsa/pumps/{tag}/spare-parts")
def get_ltsa_pump_spare_parts(
    tag: str,
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
    seal_stock_gateway=Depends(get_seal_stock_gateway),
    seal_gateway=Depends(get_seal_gateway),
) -> Payload:
    return get_pump_spare_parts(
        tag,
        seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
        seal_stock_gateway=seal_stock_gateway,
        seal_gateway=seal_gateway,
    )


# Knowledge API (MWO-LTSA-031D) -- assembles LTSAKnowledgeService's
# (MWO-LTSA-031A), EquipmentTimelineService's (MWO-LTSA-031B/R1), and
# EngineeringContextEngine's already-existing outputs into one response.
# Router only: no filtering, no derivation, no business logic here --
# each service's own .build(tag) result is used unchanged, avoiding a
# second, drifting definition of a shape that already lives elsewhere
# (the same discipline models/responses.py's Payload comment documents
# for every other pass-through endpoint in this file).


@router.get("/api/ltsa/pumps/{tag}/knowledge")
def get_ltsa_pump_knowledge(
    tag: str,
    ltsa_knowledge_service=Depends(get_ltsa_knowledge_service),
    equipment_timeline_service=Depends(get_equipment_timeline_service),
    engineering_context_engine=Depends(get_engineering_context_engine),
) -> Payload:
    knowledge = ltsa_knowledge_service.build(tag)
    timeline = equipment_timeline_service.build(tag)
    summary = engineering_context_engine.build(tag)

    return {
        "success": True,
        "tag_number": tag,
        "data": {
            "summary": summary,
            "timeline": [dataclasses.asdict(event) for event in timeline.events],
            "seal": knowledge.seal,
            "inventory": knowledge.inventory,
            "pm": knowledge.pm_history,
            "cm": knowledge.cm_history,
            "breakdown": knowledge.breakdown_history,
            "drawings": knowledge.drawings,
            "recommendation": knowledge.recommendation,
        },
    }
