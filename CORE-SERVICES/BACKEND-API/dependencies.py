from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_API_DIR = Path(__file__).resolve().parent
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
AI5R_SDK_DIR = CORE_SERVICES_DIR.parent / "AI5R-SDK"

for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR, AI5R_SDK_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from API.cm_report_gateway import CMReportGateway
from API.condition_monitoring_reading_gateway import ConditionMonitoringReadingGateway
from API.condition_monitoring_schedule_gateway import ConditionMonitoringScheduleGateway
from API.engineering_context_engine import EngineeringContextEngine
from API.equipment_timeline_service import EquipmentTimelineService
from API.ltsa_knowledge_service import LTSAKnowledgeService
from API.maintenance_history_gateway import MaintenanceHistoryGateway
from API.pm_occurrence_gateway import PMOccurrenceGateway
from API.pm_schedule_gateway import PMScheduleGateway
from API.pump_gateway import PumpGateway
from API.seal_gateway import SealGateway
from API.seal_pump_compatibility_gateway import SealPumpCompatibilityGateway
from API.seal_stock_gateway import SealStockGateway
from API.work_order_gateway import WorkOrderGateway

PRODUCT_NAME = os.getenv("AI5R_PRODUCT_NAME", "LTSA-BRAIN")

_pump_gateway = PumpGateway()
_work_order_gateway = WorkOrderGateway()
_maintenance_history_gateway = MaintenanceHistoryGateway()
_pm_schedule_gateway = PMScheduleGateway()
_cm_report_gateway = CMReportGateway()
_condition_monitoring_schedule_gateway = ConditionMonitoringScheduleGateway()
_condition_monitoring_reading_gateway = ConditionMonitoringReadingGateway()
_pm_occurrence_gateway = PMOccurrenceGateway()
_seal_gateway = SealGateway()
_seal_stock_gateway = SealStockGateway()
_seal_pump_compatibility_gateway = SealPumpCompatibilityGateway()

# MWO-LTSA-031D -- built from the same singleton Gateway instances above,
# not fresh ones -- no second set of Gateways is constructed anywhere.
_ltsa_knowledge_service = LTSAKnowledgeService(
    pump_gateway=_pump_gateway,
    maintenance_history_gateway=_maintenance_history_gateway,
    pm_occurrence_gateway=_pm_occurrence_gateway,
    cm_report_gateway=_cm_report_gateway,
    seal_gateway=_seal_gateway,
    seal_stock_gateway=_seal_stock_gateway,
    seal_pump_compatibility_gateway=_seal_pump_compatibility_gateway,
    work_order_gateway=_work_order_gateway,
)

_equipment_timeline_service = EquipmentTimelineService(knowledge_service=_ltsa_knowledge_service)

_engineering_context_engine = EngineeringContextEngine(
    pump_gateway=_pump_gateway,
    maintenance_history_gateway=_maintenance_history_gateway,
    pm_occurrence_gateway=_pm_occurrence_gateway,
    pm_schedule_gateway=_pm_schedule_gateway,
    cm_report_gateway=_cm_report_gateway,
    condition_monitoring_reading_gateway=_condition_monitoring_reading_gateway,
    seal_gateway=_seal_gateway,
    seal_stock_gateway=_seal_stock_gateway,
    seal_pump_compatibility_gateway=_seal_pump_compatibility_gateway,
    work_order_gateway=_work_order_gateway,
)


def get_product_name() -> str:
    return PRODUCT_NAME


def get_pump_gateway() -> PumpGateway:
    return _pump_gateway


def get_work_order_gateway() -> WorkOrderGateway:
    return _work_order_gateway


def get_maintenance_history_gateway() -> MaintenanceHistoryGateway:
    return _maintenance_history_gateway


def get_pm_schedule_gateway() -> PMScheduleGateway:
    return _pm_schedule_gateway


def get_cm_report_gateway() -> CMReportGateway:
    return _cm_report_gateway


def get_condition_monitoring_schedule_gateway() -> ConditionMonitoringScheduleGateway:
    return _condition_monitoring_schedule_gateway


def get_condition_monitoring_reading_gateway() -> ConditionMonitoringReadingGateway:
    return _condition_monitoring_reading_gateway


def get_pm_occurrence_gateway() -> PMOccurrenceGateway:
    return _pm_occurrence_gateway


def get_seal_gateway() -> SealGateway:
    return _seal_gateway


def get_seal_stock_gateway() -> SealStockGateway:
    return _seal_stock_gateway


def get_seal_pump_compatibility_gateway() -> SealPumpCompatibilityGateway:
    return _seal_pump_compatibility_gateway


def get_ltsa_knowledge_service() -> LTSAKnowledgeService:
    return _ltsa_knowledge_service


def get_equipment_timeline_service() -> EquipmentTimelineService:
    return _equipment_timeline_service


def get_engineering_context_engine() -> EngineeringContextEngine:
    return _engineering_context_engine
