from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_API_DIR = Path(__file__).resolve().parent
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
REPO_ROOT = CORE_SERVICES_DIR.parent
AI5R_SDK_DIR = REPO_ROOT / "AI5R-SDK"
INGESTION_DIR = REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"

for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR, AI5R_SDK_DIR, INGESTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from API.cm_report_gateway import CMReportGateway
from API.condition_monitoring_reading_gateway import ConditionMonitoringReadingGateway
from API.condition_monitoring_schedule_gateway import ConditionMonitoringScheduleGateway
from API.engineering_context_engine import EngineeringContextEngine
from API.equipment_timeline_service import EquipmentTimelineService
from API.fleet_executive_summary import FleetExecutiveSummaryService
from API.fleet_reliability_service import FleetReliabilityService
from API.import_session_repository import ImportSessionRepository
from API.ltsa_knowledge_service import LTSAKnowledgeService
from API.maintenance_history_gateway import MaintenanceHistoryGateway
from API.pm_occurrence_gateway import PMOccurrenceGateway
from API.pm_schedule_gateway import PMScheduleGateway
from API.pump_gateway import PumpGateway
from API.seal_engineering_document_gateway import SealEngineeringDocumentGateway
from API.seal_gateway import SealGateway
from API.seal_pump_compatibility_gateway import SealPumpCompatibilityGateway
from API.seal_stock_gateway import SealStockGateway
from API.work_order_gateway import WorkOrderGateway
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner

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
_seal_engineering_document_gateway = SealEngineeringDocumentGateway()

# Import API Foundation -- in-memory only, no SQL/schema (see
# API.import_session_repository's own header comment).
_import_session_repository = ImportSessionRepository()

# MWO-LTSA-DATA-IMPORT-UI-001B -- the one, real, live-DB-capable
# DatabaseRunner this backend process holds, needed so
# POST /api/ltsa/import/pump-xlsx/dry-run (and POST /api/ltsa/import/
# execute) can reach a real database. Same DatabaseConfig/DatabaseRunner
# (PRODUCTS/LTSA-BRAIN/INGESTION/ltsa_pump_inventory_db_upsert.py, reused
# unmodified) and the same env-file/compose-file runtime every test file
# in this session already targets. DatabaseRunner.__init__ does no I/O of
# its own -- it only stores config; every subprocess call happens inside
# execute_script()/query_scalar(), called lazily, per request.
_import_database_runner = DatabaseRunner(
    DatabaseConfig(
        env_file=CORE_SERVICES_DIR / "RUNTIME" / ".env.verify.local",
        compose_file=CORE_SERVICES_DIR / "RUNTIME" / "compose.yaml",
    )
)

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
    seal_engineering_document_gateway=_seal_engineering_document_gateway,
    pm_schedule_gateway=_pm_schedule_gateway,
    condition_monitoring_schedule_gateway=_condition_monitoring_schedule_gateway,
)

_equipment_timeline_service = EquipmentTimelineService(knowledge_service=_ltsa_knowledge_service)

# MWO-LTSA-037C -- built from the same singleton PumpGateway and
# LTSAKnowledgeService above, not fresh ones -- no second aggregate.
_fleet_reliability_service = FleetReliabilityService(
    pump_gateway=_pump_gateway,
    ltsa_knowledge_service=_ltsa_knowledge_service,
)

# MWO-LTSA-038A -- built from the same singleton FleetReliabilityService
# above, not a fresh one -- no second aggregate.
_fleet_executive_summary_service = FleetExecutiveSummaryService(
    fleet_reliability_service=_fleet_reliability_service,
)

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


def get_import_session_repository() -> ImportSessionRepository:
    return _import_session_repository


def get_import_database_runner() -> DatabaseRunner:
    return _import_database_runner


def get_ltsa_knowledge_service() -> LTSAKnowledgeService:
    return _ltsa_knowledge_service


def get_equipment_timeline_service() -> EquipmentTimelineService:
    return _equipment_timeline_service


def get_fleet_reliability_service() -> FleetReliabilityService:
    return _fleet_reliability_service


def get_fleet_executive_summary_service() -> FleetExecutiveSummaryService:
    return _fleet_executive_summary_service


def get_engineering_context_engine() -> EngineeringContextEngine:
    return _engineering_context_engine
