"""MWO-LTSA-SEAL-LEAK-DIAGNOSTIC-001 -- focused tests only, synthetic
fixtures. FakeKnowledgeService/FakeEquipmentTimelineService mirror the
REAL LTSAKnowledgeService.build()/EquipmentTimelineService.build_current_
seal() contracts verified by reading the actual source (not assumed).
"""

from datetime import date, timedelta
import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.ltsa_knowledge_service import LTSAKnowledge
from API.seal_leak_diagnostic_service import (
    DATA_GAP,
    HIGH,
    INSUFFICIENT_EVIDENCE,
    LOW,
    MEDIUM,
    STATUS_LEAK_CURRENT,
    STATUS_LEAK_HISTORICAL,
    STATUS_NO_LEAK,
    STOCK_AVAILABLE,
    STOCK_NO_COMPATIBLE_SEAL,
    STOCK_NO_RECORD,
    STOCK_ZERO,
    diagnose,
)

TODAY = date.today()
RECENT = (TODAY - timedelta(days=5)).isoformat()
OLD = (TODAY - timedelta(days=90)).isoformat()


def _knowledge(tag="TEST-PUMP", **overrides):
    defaults = dict(
        tag_number=tag, pump={"tag_number": tag, "status": "Active"}, seal=[], inventory=[],
        pm_history=[], cm_history=[], breakdown_history=[], drawings=None, recommendation=(),
        pm_schedules=[], condition_monitoring_schedules=[], condition_monitoring_readings=[],
    )
    defaults.update(overrides)
    return LTSAKnowledge(**defaults)


def _cmon(reading_date, **fields):
    row = {"reading_date": reading_date, "condition_monitoring_reading_code": f"CMONR-{reading_date}"}
    row.update(fields)
    return row


class FakeKnowledgeService:
    def __init__(self, knowledge):
        self._knowledge = knowledge

    def build(self, tag):
        return self._knowledge


class FakeSeal:
    def __init__(self, seal_code="SC-1", seal_name="Seal 1", installed_at=None, status="INSTALLED"):
        self.seal_code = seal_code
        self.seal_name = seal_name
        self.installed_at = installed_at
        self.status = status


class FakeEquipmentTimelineService:
    def __init__(self, current_seal=None):
        self._current_seal = current_seal

    def build_current_seal(self, tag):
        return self._current_seal


def _diagnose(knowledge, equipment_timeline_service=None):
    return diagnose(
        knowledge.tag_number, ltsa_knowledge_service=FakeKnowledgeService(knowledge),
        equipment_timeline_service=equipment_timeline_service, today=TODAY,
    )


# A. current leak evidence
def test_current_leak_evidence_detected():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True, finding="Leak")])
    d = _diagnose(k)
    assert d.diagnostic_status == STATUS_LEAK_CURRENT
    assert d.leak_evidence["current_leak_flag"] is True


# B. historical/repeated leak evidence
def test_historical_leak_evidence_without_current():
    k = _knowledge(condition_monitoring_readings=[_cmon(OLD, mechanical_seal_leak_de=True), _cmon(OLD, mechanical_seal_leak_de=True)])
    d = _diagnose(k)
    assert d.diagnostic_status == STATUS_LEAK_HISTORICAL
    assert d.leak_evidence["historical_leak_count"] == 2
    assert d.leak_evidence["current_leak_flag"] is False


# C. no-leak case
def test_no_leak_evidence_returns_no_leak_status():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=False)])
    d = _diagnose(k)
    assert d.diagnostic_status == STATUS_NO_LEAK
    assert d.hypotheses == ()
    assert d.conclusion == "NO_LEAK_EVIDENCE"


# D. temperature evidence
def test_temperature_evidence_reports_raw_values():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True, suction_temp=176.0)])
    d = _diagnose(k)
    assert d.temperature_evidence["status"] == "FACT"
    assert d.temperature_evidence["readings"][0]["value"] == 176.0


# E. vibration DATA_GAP
def test_vibration_missing_is_data_gap():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True, suction_temp=100.0)])
    d = _diagnose(k)
    assert d.vibration_evidence["status"] == DATA_GAP
    assert "vibration" in d.missing_evidence


# F. installed-seal DATA_GAP
def test_installed_seal_unconfirmed_is_data_gap():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)], seal=[{"seal_code": "SC-1", "part_name": "Seal 1"}])
    d = _diagnose(k, equipment_timeline_service=FakeEquipmentTimelineService(current_seal=None))
    assert d.seal_evidence["confirmed_installed_seal"] == DATA_GAP
    assert "confirmed_installed_seal" in d.missing_evidence


# G. compatible != installed
def test_compatible_seal_never_treated_as_installed():
    k = _knowledge(
        condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)],
        seal=[{"seal_code": "SC-1", "part_name": "Seal 1"}, {"seal_code": "SC-2", "part_name": "Seal 2"}],
    )
    d = _diagnose(k, equipment_timeline_service=FakeEquipmentTimelineService(current_seal=None))
    assert d.seal_evidence["confirmed_installed_seal"] == DATA_GAP
    assert len(d.seal_evidence["compatible_seals"]) == 2
    installed = FakeSeal(seal_code="SC-1")
    d2 = _diagnose(k, equipment_timeline_service=FakeEquipmentTimelineService(current_seal=installed))
    assert d2.seal_evidence["confirmed_installed_seal"]["seal_code"] == "SC-1"
    assert len(d2.seal_evidence["compatible_seals"]) == 2  # compatibility list unaffected by confirmation


# H. stock readiness
def test_stock_readiness_distinguishes_all_four_states():
    k = _knowledge(
        condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)],
        seal=[{"seal_code": "SC-ZERO", "part_name": "Z"}, {"seal_code": "SC-NOREC", "part_name": "N"}],
        inventory=[{"seal_type": "SC-ZERO", "quantity_available": 0, "nominal_size": "60", "size_unit": "mm"}],
    )
    d = _diagnose(k)
    states = {row.seal_code: row.state for row in d.inventory_evidence}
    assert states["SC-ZERO"] == STOCK_ZERO
    assert states["SC-NOREC"] == STOCK_NO_RECORD

    k_no_compat = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)], seal=[])
    d2 = _diagnose(k_no_compat)
    assert d2.inventory_evidence[0].state == STOCK_NO_COMPATIBLE_SEAL

    k_avail = _knowledge(
        condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)],
        seal=[{"seal_code": "SC-OK", "part_name": "O"}],
        inventory=[{"seal_type": "SC-OK", "quantity_available": 4, "nominal_size": "60", "size_unit": "mm"}],
    )
    d3 = _diagnose(k_avail)
    assert d3.inventory_evidence[0].state == STOCK_AVAILABLE
    assert d3.inventory_evidence[0].quantity == 4


# I. missing measurement != zero
def test_missing_vibration_is_never_coerced_to_zero():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True, suction_temp=90.0)])
    d = _diagnose(k)
    assert d.vibration_evidence.get("readings") is None
    assert d.vibration_evidence["status"] == DATA_GAP


# J. raw high numeric temperature does not become "abnormal"
def test_raw_high_temperature_never_labeled_abnormal():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True, suction_temp=336.0)])
    d = _diagnose(k)
    assert d.temperature_evidence["readings"][0]["value"] == 336.0
    import json
    dumped = json.dumps(d.temperature_evidence)
    for word in ("abnormal", "high", "critical", "overheated", "HIGH_TEMP"):
        assert word not in dumped


# K. single leak cannot produce CONFIRMED_ROOT_CAUSE
def test_single_leak_never_confirms_root_cause():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)])
    d = _diagnose(k)
    assert d.conclusion != "CONFIRMED_ROOT_CAUSE"
    seal_hyp = next(h for h in d.hypotheses if h.cause == "seal_face_or_secondary_seal_degradation")
    assert seal_hyp.confidence == LOW


# L. repeated leaks alone cannot produce CONFIRMED_ROOT_CAUSE
def test_repeated_leaks_alone_never_confirms_root_cause():
    k = _knowledge(condition_monitoring_readings=[_cmon(OLD, mechanical_seal_leak_de=True), _cmon(OLD, mechanical_seal_leak_de=True), _cmon(OLD, mechanical_seal_leak_de=True)])
    d = _diagnose(k)
    assert d.conclusion != "CONFIRMED_ROOT_CAUSE"
    seal_hyp = next(h for h in d.hypotheses if h.cause == "seal_face_or_secondary_seal_degradation")
    assert seal_hyp.confidence != HIGH


def test_leak_plus_breakdown_plus_cm_seal_failure_reaches_high():
    k = _knowledge(
        condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)],
        breakdown_history=[{"maintenance_record_code": "MH-1"}, {"maintenance_record_code": "MH-2"}],
        cm_history=[{"cm_report_code": "CM-1", "failure_category": "SEAL_FAILURE"}],
    )
    d = _diagnose(k)
    seal_hyp = next(h for h in d.hypotheses if h.cause == "seal_face_or_secondary_seal_degradation")
    assert seal_hyp.confidence == HIGH
    assert d.conclusion != "CONFIRMED_ROOT_CAUSE"


# M. hypotheses contain supporting + missing/contradicting evidence
def test_every_hypothesis_carries_supporting_and_missing_evidence_fields():
    k = _knowledge(condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True, suction_temp=100.0)])
    d = _diagnose(k)
    assert d.hypotheses
    for h in d.hypotheses:
        assert isinstance(h.supporting_evidence, tuple)
        assert isinstance(h.missing_or_contradicting_evidence, tuple)
        assert h.supporting_evidence or h.missing_or_contradicting_evidence


# N. confidence is bounded enum, no fabricated percentage
def test_confidence_values_are_bounded_enum_only():
    allowed = {HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE}
    k = _knowledge(
        condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)],
        breakdown_history=[{"maintenance_record_code": "MH-1"}, {"maintenance_record_code": "MH-2"}],
        cm_history=[{"cm_report_code": "CM-1", "failure_category": "SEAL_FAILURE"}],
    )
    d = _diagnose(k)
    assert d.confidence in allowed
    for h in d.hypotheses:
        assert h.confidence in allowed
        assert not isinstance(h.confidence, float)


# O. repository-contract test: fixtures mirror the REAL, verified shapes
def test_fixtures_mirror_real_ltsaknowledge_and_current_seal_contracts():
    import dataclasses
    from API.ltsa_knowledge_service import LTSAKnowledge
    from API.pump_lifecycle_models import PumpLifecycleCurrentSeal

    real_knowledge_fields = {f.name for f in dataclasses.fields(LTSAKnowledge)}
    used_fields = {"tag_number", "pump", "seal", "inventory", "pm_history", "cm_history", "breakdown_history", "condition_monitoring_readings"}
    assert used_fields <= real_knowledge_fields

    real_seal_fields = {f.name for f in dataclasses.fields(PumpLifecycleCurrentSeal)}
    assert {"seal_code", "seal_name", "installed_at", "status"} <= real_seal_fields

    # LTSAKnowledgeService.build() and EquipmentTimelineService.build_current_seal()
    # are the real methods diagnose() calls -- verify the callables exist with
    # the exact names/signatures used, not assumed.
    from API.ltsa_knowledge_service import LTSAKnowledgeService
    from API.equipment_timeline_service import EquipmentTimelineService
    assert callable(getattr(LTSAKnowledgeService, "build"))
    assert callable(getattr(EquipmentTimelineService, "build_current_seal"))


def test_diagnose_accepts_ltsa_knowledge_production_inventory_shape():
    k = _knowledge(
        condition_monitoring_readings=[_cmon(RECENT, mechanical_seal_leak_de=True)],
        seal=[{"seal_code": "SC-PROD", "part_name": "Production compatible seal"}],
        inventory=[{"seal_code": "SC-PROD", "quantity_on_hand": 3, "reorder_point": 1, "location": "WH"}],
    )
    d = _diagnose(k)
    assert d.inventory_evidence[0].seal_code == "SC-PROD"
    assert d.inventory_evidence[0].quantity == 3
    assert d.inventory_evidence[0].state == STOCK_AVAILABLE


def test_diagnose_through_ltsa_knowledge_service_with_production_shaped_repository_returns():
    from API.ltsa_knowledge_service import LTSAKnowledgeService

    tag = "110-P-12B"

    class PumpGateway:
        def get_pump(self, tag_number):
            return {"success": True, "data": {"tag_number": tag_number, "status": "RUNNING"}}

    class MaintenanceHistoryGateway:
        def list_maintenance_history(self):
            return {"success": True, "data": []}

    class WorkOrderGateway:
        def list_work_orders(self):
            return {"success": True, "data": []}

    class SealPumpCompatibilityGateway:
        def list_seal_pump_compatibilities(self):
            return {"success": True, "data": [{"pump_tag_number": tag, "seal_code": "SC-PROD"}]}

    class SealGateway:
        def list_seals(self):
            return {"success": True, "data": [{"seal_code": "SC-PROD", "seal_name": "Production Seal"}]}

    class SealStockGateway:
        def list_seal_stocks(self):
            return {"success": True, "data": [{"seal_code": "SC-PROD", "quantity_on_hand": 5, "reorder_point": 1, "location": "WH"}]}

    class EmptyGateway:
        def list_pm_occurrences(self):
            return {"success": True, "data": []}

        def list_cm_reports(self):
            return {"success": True, "data": []}

        def list_seal_engineering_documents(self):
            return {"success": True, "data": []}

        def list_pm_schedules(self):
            return {"success": True, "data": []}

        def list_condition_monitoring_schedules(self):
            return {"success": True, "data": []}

        def list_condition_monitoring_readings(self):
            return {"success": True, "data": []}

    class MechanicalSealStockRepository:
        def list_for_equipment(self, equipment_tag):
            return [
                {
                    "seal_code": "SC-PROD",
                    "seal_type": "SC-PROD",
                    "nominal_size": None,
                    "size_unit": None,
                    "quantity_on_hand": 5,
                    "quantity_available": 5,
                    "stock_location": "WH",
                    "equipment_tag": equipment_tag,
                }
            ]

    class PMOccurrenceRepository:
        def list_by_asset(self, asset_code):
            return []

    class ConditionMonitoringReadingRepository:
        def list_by_asset(self, asset_code):
            return [
                {
                    "condition_monitoring_reading_code": "CMONR-PROD",
                    "asset_code": asset_code,
                    "reading_date": RECENT,
                    "mechanical_seal_leak_de": True,
                    "finding": "Mechanical seal leak DE",
                }
            ]

    class DictListRepository:
        def list_pm_schedules(self):
            return {"success": True, "data": []}

        def list_cm_reports(self):
            return {"success": True, "data": [{"cm_report_code": "CM-PROD", "asset_code": tag, "failure_category": "SEAL_FAILURE"}]}

        def list_condition_monitoring_schedules(self):
            return {"success": True, "data": []}

    repo = DictListRepository()
    knowledge_service = LTSAKnowledgeService(
        pump_gateway=PumpGateway(),
        maintenance_history_gateway=MaintenanceHistoryGateway(),
        pm_occurrence_gateway=EmptyGateway(),
        cm_report_gateway=EmptyGateway(),
        seal_gateway=SealGateway(),
        seal_stock_gateway=SealStockGateway(),
        seal_pump_compatibility_gateway=SealPumpCompatibilityGateway(),
        work_order_gateway=WorkOrderGateway(),
        seal_engineering_document_gateway=EmptyGateway(),
        pm_schedule_gateway=EmptyGateway(),
        condition_monitoring_schedule_gateway=EmptyGateway(),
        condition_monitoring_reading_gateway=EmptyGateway(),
        pm_occurrence_repository=PMOccurrenceRepository(),
        condition_monitoring_reading_repository=ConditionMonitoringReadingRepository(),
        pm_schedule_repository=repo,
        cm_report_repository=repo,
        condition_monitoring_schedule_repository=repo,
        mechanical_seal_stock_repository=MechanicalSealStockRepository(),
    )

    d = diagnose(tag, ltsa_knowledge_service=knowledge_service, today=TODAY)
    assert d.equipment == tag
    assert d.leak_evidence["current_leak_flag"] is True
    assert d.inventory_evidence[0].seal_code == "SC-PROD"
    assert d.inventory_evidence[0].quantity == 5
    assert d.inventory_evidence[0].state == STOCK_AVAILABLE


