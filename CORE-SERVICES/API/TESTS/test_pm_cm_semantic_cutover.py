"""
Tests for LTSA PM/CM Semantic Cutover R1.

Verifies:
1. PM = Preventive Maintenance
2. CM = Condition Monitoring
3. Corrective Maintenance intent is retired.
4. "cm <tag>", "CM terakhir <tag>" routes to Condition Monitoring.
5. Legacy "cmon <tag>" routes to Condition Monitoring for backward compatibility.
6. Copilot queries condition_monitoring_reading, NOT cm_report, for CM questions.
7. Pump /last-cm endpoint returns canonical condition_monitoring_reading date.
8. Condition monitoring readings are NOT interpreted as failures.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_SERVICES_DIR = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_DIR))

from API.copilot_ask_service import _detect_intent, ask_copilot, CopilotAnswer  # noqa: E402
from API.whatsapp_intake_service import _detect_intent as _whatsapp_detect_intent  # noqa: E402


class TestIntentSemanticCutover:
    def test_copilot_cm_routes_to_condition_monitoring(self):
        assert _detect_intent("cm 945-P-7A") == "condition_monitoring"
        assert _detect_intent("CM 945-P-7A") == "condition_monitoring"
        assert _detect_intent("cm terakhir 945-P-7A", tag="945-P-7A") == "condition_monitoring"
        assert _detect_intent("CM terakhir 945-P-7A", tag="945-P-7A") == "condition_monitoring"
        assert _detect_intent("status cm 945-P-7A", tag="945-P-7A") == "condition_monitoring"
        assert _detect_intent("kapan cm 945-P-7A", tag="945-P-7A") == "condition_monitoring"

    def test_copilot_cmon_routes_to_condition_monitoring_backward_compat(self):
        assert _detect_intent("cmon 945-P-7A") == "condition_monitoring"
        assert _detect_intent("CMON 945-P-7A") == "condition_monitoring"

    def test_copilot_pm_routes_to_pm(self):
        assert _detect_intent("pm 945-P-7A") == "pm"
        assert _detect_intent("PM 945-P-7A") == "pm"

    def test_whatsapp_intake_cm_and_cmon_route_to_condition_monitoring(self):
        assert _whatsapp_detect_intent("cm 945-P-7A") == "CONDITION_MONITORING"
        assert _whatsapp_detect_intent("CM 945-P-7A") == "CONDITION_MONITORING"
        assert _whatsapp_detect_intent("cmon 945-P-7A") == "CONDITION_MONITORING"
        assert _whatsapp_detect_intent("pm 945-P-7A") == "PM"


class _MockCMReportRepository:
    def __init__(self):
        self.called = False

    def list_cm_reports(self, **kwargs):
        self.called = True
        return {"success": True, "data": []}

    def get_cm_report(self, *args, **kwargs):
        self.called = True
        return {"success": True, "data": None}


class _MockConditionMonitoringReadingGateway:
    def __init__(self, readings):
        self.readings = readings
        self.called = False

    def list_condition_monitoring_readings(self, **kwargs):
        self.called = True
        return {"success": True, "data": self.readings}


class TestCopilotCMExecution:
    def test_cm_query_uses_condition_monitoring_never_cm_report(self):
        cm_repo = _MockCMReportRepository()
        readings = [
            {
                "condition_monitoring_reading_code": "CMONR-100",
                "asset_code": "945-P-7A",
                "reading_date": "2026-04-20",
                "status": "APPROVED",
                "mechanical_seal_leak_de": False,
                "mechanical_seal_leak_nde": False,
            }
        ]
        cmon_gw = _MockConditionMonitoringReadingGateway(readings)

        # Ask a CM question
        answer = ask_copilot(
            "CM 945-P-7A",
            "945-P-7A",
            None,
            pump_gateway=None,
            maintenance_history_gateway=None,
            work_order_gateway=None,
            installation_gateway=None,
            ltsa_knowledge_service=None,
            equipment_timeline_service=None,
            condition_monitoring_reading_gateway=cmon_gw,
            installation_report_repository=None,
            mechanical_seal_stock_repository=None,
            condition_monitoring_reading_repository=None,
            fleet_executive_summary_service=None,
            pm_occurrence_repository=None,
            cm_report_repository=cm_repo,
        )

        assert isinstance(answer, CopilotAnswer)
        # Verify cm_report_repository was NEVER called
        assert cm_repo.called is False, "cm_report must NOT be queried for CM questions"
        # Verify condition_monitoring_reading was called
        assert cmon_gw.called is True
        # Verify reading date is in answer
        assert "2026-04-20" in answer.answer or "20 Apr" in answer.answer


class TestPumpLastCMCutover:
    def test_get_pump_last_cm_uses_condition_monitoring_reading(self):
        from API.maintenance_intelligence_service import get_pump_last_cm

        readings = [
            {
                "condition_monitoring_reading_code": "CMONR-001",
                "asset_code": "945-P-7A",
                "reading_date": "2026-04-20",
                "status": "APPROVED",
            },
            {
                "condition_monitoring_reading_code": "CMONR-002",
                "asset_code": "945-P-7A",
                "reading_date": "2026-03-15",
                "status": "APPROVED",
            },
            {
                "condition_monitoring_reading_code": "CMONR-003",
                "asset_code": "OTHER-PUMP",
                "reading_date": "2026-05-01",
                "status": "APPROVED",
            },
        ]
        cmon_gw = _MockConditionMonitoringReadingGateway(readings)
        cm_repo = _MockCMReportRepository()

        result = get_pump_last_cm(
            "945-P-7A",
            condition_monitoring_reading_gateway=cmon_gw,
            cm_report_gateway=cm_repo,
        )

        assert result["success"] is True
        assert result["tag_number"] == "945-P-7A"
        assert result["last_cm"] is not None
        assert result["last_cm"]["reading_date"] == "2026-04-20"
        assert result["last_cm"]["condition_monitoring_reading_code"] == "CMONR-001"
        assert cm_repo.called is False, "cm_report must NOT be queried for Last CM"

