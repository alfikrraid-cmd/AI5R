"""MWO-LTSA-EQUIPMENT-360-001 -- Phase 5 (regression) and Phase 6 (negative
safety) tests for the canonical Equipment 360 fix.

Controlled fixture, one canonical asset (211-P-13AR) plus one sister asset
(211-P-1A) with DELIBERATELY different facts, so a cross-contamination bug
would fail loudly rather than silently pass. Every one of the 7 query
paths named in this MWO's own Phase 1 trace is exercised here via
ask_copilot() (the single canonical dispatcher), and get_equipment_360()
(the canonical aggregator) is checked to agree with every one of them --
proving "same equipment + same database state = same underlying facts"
directly, not by inspection.
"""

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = API_DIR.parent
for _path in (CORE_SERVICES_DIR,):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from API.copilot_ask_service import ask_copilot, DATA_GAP, FACT  # noqa: E402
from API.equipment_360_service import get_equipment_360  # noqa: E402
from API.equipment_timeline_service import PumpLifecycleCurrentSeal  # noqa: E402
from API.ltsa_knowledge_service import LTSAKnowledge  # noqa: E402
from API.whatsapp_intake_service import _normalize_pump_tag_text  # noqa: E402

TAG = "211-P-13AR"
SISTER_TAG = "211-P-1A"

# --- Fixture: one canonical, controlled set of facts for TAG, and a
# deliberately different set for SISTER_TAG -- MWO's own Phase 6 asset-
# isolation requirement. ---

_PUMPS = {
    TAG: {"tag_number": TAG, "status": "Active", "area": "FRAKSINASI", "location": "Unit 2 Fraksinasi", "pump_type": "Centrifugal"},
    SISTER_TAG: {"tag_number": SISTER_TAG, "status": "Idle", "area": "UTILITAS", "location": "Unit 5 Utilitas", "pump_type": "Centrifugal"},
}

_PM_RECORDS = {
    TAG: [
        {"pm_occurrence_code": "PM-13AR-002", "occurrence_date": "2026-08-29", "workflow_status": "CONFIRMED", "provenance": "SAP"},
        {"pm_occurrence_code": "PM-13AR-001", "occurrence_date": "2026-05-01", "workflow_status": "CONFIRMED", "provenance": "SAP"},
    ],
    SISTER_TAG: [
        {"pm_occurrence_code": "PM-1A-001", "occurrence_date": "2026-07-01", "workflow_status": "CONFIRMED", "provenance": "SAP"},
    ],
}

_CMON_RECORDS = {
    TAG: [
        {
            "condition_monitoring_reading_code": "CMON-13AR-001",
            "reading_date": "2026-08-25",
            "finding": "mechanical seal leak",
            "workflow_status": "DRAFT",
            "technical_recommendation": "Monitor closely, schedule inspection.",
            "source_reference": "Inspector A",
        },
    ],
    SISTER_TAG: [],
}

# CM: no confirmed corrective-maintenance record exists for TAG -- must be
# reported as a truthful FACT (no record found), never DATA_GAP and never
# borrowed from SISTER_TAG.
_CM_RECORDS = {
    SISTER_TAG: [
        {"cm_report_code": "CM-1A-001", "asset_code": SISTER_TAG, "severity": "MEDIUM", "status": "CLOSED"},
    ],
}

_STOCK_POOLS = [
    {
        "stock_pool_id": "POOL-T6014DP",
        "seal_type": "T6014DP",
        "quantity_available": 4,
        "stock_location": None,
        "applications": [{"equipment_tag": TAG}],
    },
]


class _FakePumpGateway:
    def get_pump(self, tag_number):
        pump = _PUMPS.get(tag_number)
        return {"success": bool(pump), "data": pump}


class _FakePMOccurrenceRepository:
    def list_by_asset(self, asset_code):
        return list(_PM_RECORDS.get(asset_code, []))


class _FakeCMReportRepository:
    def list_cm_reports(self, **_kwargs):
        return {"success": True, "data": list(_CM_RECORDS.get(SISTER_TAG, []))}


class _FakeConditionMonitoringReadingRepository:
    def list_by_asset(self, asset_code):
        return list(_CMON_RECORDS.get(asset_code, []))


class _FakeEquipmentTimelineService:
    # No confirmed current-seal installation record exists for TAG --
    # Phase 5's own fixture requirement ("if no confirmed installed seal
    # exists, all relevant intents must say so").
    def build_current_seal(self, tag_number):
        return None


class _FakeLTSAKnowledgeService:
    def build(self, tag_number):
        seals = [{"seal_code": "T6014DP", "part_name": "Mechanical Seal T6014DP"}] if tag_number == TAG else []
        return LTSAKnowledge(
            tag_number=tag_number, pump=_PUMPS.get(tag_number), seal=seals, inventory=[],
            pm_history=[], cm_history=[], breakdown_history=[], drawings=[],
            recommendation=(), pm_schedules=[], condition_monitoring_schedules=[],
            condition_monitoring_readings=[],
        )


class _FakeMechanicalSealStockRepository:
    def list_pools(self, limit=200):
        return {"success": True, "data": _STOCK_POOLS}


class _FakeMaintenanceHistoryGateway:
    def list_maintenance_history(self):
        return {"success": True, "data": []}


def _deps(**overrides):
    base = dict(
        pump_gateway=_FakePumpGateway(),
        maintenance_history_gateway=_FakeMaintenanceHistoryGateway(),
        work_order_gateway=None,
        installation_gateway=None,
        ltsa_knowledge_service=_FakeLTSAKnowledgeService(),
        equipment_timeline_service=_FakeEquipmentTimelineService(),
        condition_monitoring_reading_gateway=None,
        installation_report_repository=None,
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository(),
        condition_monitoring_reading_repository=_FakeConditionMonitoringReadingRepository(),
        fleet_executive_summary_service=None,
        pm_occurrence_repository=_FakePMOccurrenceRepository(),
        cm_report_repository=_FakeCMReportRepository(),
    )
    base.update(overrides)
    return base


def _ask(question, tag=TAG, **overrides):
    return ask_copilot(question, tag, None, **_deps(**overrides))


def _equipment_360(tag=TAG):
    deps = _deps()
    return get_equipment_360(
        tag,
        pump_gateway=deps["pump_gateway"],
        pm_occurrence_repository=deps["pm_occurrence_repository"],
        cm_report_repository=deps["cm_report_repository"],
        condition_monitoring_reading_repository=deps["condition_monitoring_reading_repository"],
        equipment_timeline_service=deps["equipment_timeline_service"],
        ltsa_knowledge_service=deps["ltsa_knowledge_service"],
        mechanical_seal_stock_repository=deps["mechanical_seal_stock_repository"],
    )


# --- Phase 5: tag resolution for the "211p13ar" variant spelling ---

def test_tag_normalization_resolves_variant_spelling_to_canonical_tag():
    for text in ("Bagaimana kondisi 211-P-13AR?", "PM terakhir 211-P-13AR", "CMON terakhir 211p13ar",
                 "CM terakhir 211p13ar", "Mechanical seal 211p13ar apa?", "Ada stock seal untuk 211p13ar?",
                 "History 211p13ar"):
        assert _normalize_pump_tag_text(text) == TAG


# --- Phase 5: the 7 named query paths, each a truthful, canonical answer ---

def test_summary_query_reports_area_fraksinasi_and_active_status():
    answer = _ask("Bagaimana kondisi 211-P-13AR?")
    assert answer.kind == FACT
    assert "FRAKSINASI" in answer.answer
    assert "Active" in answer.answer


def test_pm_query_reports_latest_pm_date_and_status():
    answer = _ask("PM terakhir 211-P-13AR")
    assert answer.kind == FACT
    assert "2026-08-29" in answer.answer
    assert "CONFIRMED" in answer.answer


def test_cmon_query_reports_leak_finding_and_draft_status():
    answer = _ask("CMON terakhir 211-P-13AR")
    assert answer.kind == FACT
    assert "mechanical seal leak" in answer.answer
    assert "DRAFT" in answer.answer


def test_cm_query_reports_no_cm_record_as_truthful_fact():
    answer = _ask("CM terakhir 211-P-13AR")
    assert answer.kind == FACT
    assert "No corrective maintenance" in answer.answer


def test_current_seal_query_reports_no_confirmed_installation():
    answer = _ask("Mechanical seal terakhir 211-P-13AR apa?")
    assert answer.kind == DATA_GAP
    assert "No confirmed current-seal installation record" in answer.answer


def test_stock_query_reports_available_quantity_never_zero():
    answer = _ask("Ada stock seal untuk 211-P-13AR?")
    assert answer.kind == FACT
    assert "4 unit" in answer.answer
    assert "0 available" not in answer.answer


def test_history_query_never_crashes_and_reports_truthfully():
    answer = _ask("History 211-P-13AR")
    assert answer.kind == FACT
    assert "No maintenance history" in answer.answer


# --- Phase 5: cross-query consistency against the canonical aggregator ---

def test_cross_query_consistency_against_equipment_360_aggregator():
    e360 = _equipment_360()
    assert e360.area == "FRAKSINASI"
    assert e360.status == "Active"
    assert e360.pm_latest["occurrence_date"] == "2026-08-29"
    assert e360.cmon_latest["finding"] == "mechanical seal leak"
    assert e360.cmon_latest["workflow_status"] == "DRAFT"
    assert e360.cm_latest is None
    assert e360.current_seal is None
    assert any(s.get("seal_code") == "T6014DP" for s in e360.compatible_seals)
    assert any(row["quantity_available"] == 4 for row in e360.seal_stock)

    summary = _ask("Bagaimana kondisi 211-P-13AR?")
    pm = _ask("PM terakhir 211-P-13AR")
    cmon = _ask("CMON terakhir 211-P-13AR")

    # Same equipment, same database state -- every response must agree
    # with the aggregator's own facts, regardless of which question wording
    # produced it (the exact invariant this MWO's mission text names).
    assert e360.area in summary.answer
    assert e360.pm_latest["occurrence_date"] in pm.answer
    assert e360.cmon_latest["finding"] in cmon.answer
    assert e360.cmon_latest["workflow_status"] in cmon.answer


def test_compatible_seal_never_presented_as_confirmed_installed():
    seal_answer = _ask("Mechanical seal terakhir 211-P-13AR apa?")
    # T6014DP is compatibility evidence only (current_seal is None) -- must
    # never appear in the current-seal DATA_GAP answer as if installed.
    assert "T6014DP" not in seal_answer.answer
    compat_answer = _ask("Seal compatible untuk 211-P-13AR")
    assert "T6014DP" in compat_answer.answer


# --- Phase 6: negative safety -- wrong-asset isolation ---

def test_sister_asset_query_never_leaks_into_canonical_asset_answer():
    summary = _ask("Bagaimana kondisi 211-P-13AR?")
    assert SISTER_TAG not in summary.answer
    assert "UTILITAS" not in summary.answer
    assert "Idle" not in summary.answer

    pm = _ask("PM terakhir 211-P-13AR")
    assert "2026-07-01" not in pm.answer
    assert "PM-1A-001" not in pm.answer


def test_sister_asset_pm_query_returns_its_own_facts_not_canonical_assets():
    answer = _ask("PM terakhir 211-P-1A", tag=SISTER_TAG)
    assert answer.kind == FACT
    assert "2026-07-01" in answer.answer
    assert "2026-08-29" not in answer.answer


def test_no_cmon_for_sister_asset_says_so_truthfully():
    answer = _ask("CMON terakhir 211-P-1A", tag=SISTER_TAG)
    assert answer.kind == FACT
    assert "No Condition Monitoring data found" in answer.answer
    assert "mechanical seal leak" not in answer.answer


def test_no_installed_seal_never_substitutes_compatible_seal_as_installed():
    answer = _ask("Mechanical seal terakhir 211-P-13AR apa?")
    assert answer.kind == DATA_GAP
    assert "T6014DP" not in answer.answer


def test_zero_stock_never_reported_when_canonical_quantity_is_nonzero():
    answer = _ask("Ada stock seal untuk 211-P-13AR?")
    assert "tidak tersedia" not in answer.answer.lower()
    assert "kosong" not in answer.answer.lower()
    assert "0 available" not in answer.answer


def test_unregistered_field_is_data_gap_never_fabricated():
    class _FailingConditionMonitoringReadingRepository:
        def list_by_asset(self, asset_code):
            raise ConnectionError("simulated outage")

    answer = _ask("CMON terakhir 211-P-13AR", condition_monitoring_reading_repository=_FailingConditionMonitoringReadingRepository())
    assert answer.kind == DATA_GAP
    assert "mechanical seal leak" not in answer.answer


def test_equipment_360_aggregator_marks_unreachable_source_as_data_gap_not_empty():
    class _FailingCMReportRepository:
        def list_cm_reports(self, **_kwargs):
            raise ConnectionError("simulated outage")

    e360 = get_equipment_360(
        TAG,
        pump_gateway=_FakePumpGateway(),
        pm_occurrence_repository=_FakePMOccurrenceRepository(),
        cm_report_repository=_FailingCMReportRepository(),
        condition_monitoring_reading_repository=_FakeConditionMonitoringReadingRepository(),
        equipment_timeline_service=_FakeEquipmentTimelineService(),
        ltsa_knowledge_service=_FakeLTSAKnowledgeService(),
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository(),
    )
    # An unreachable source is named in data_gaps -- never silently
    # rendered the same as "confirmed zero/empty" (cm_latest is None in
    # BOTH cases, but only the gap case names "cm" in data_gaps).
    assert "cm" in e360.data_gaps
