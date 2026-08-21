import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

import pytest
from fastapi.testclient import TestClient

from main import app
from dependencies import (
    get_cm_report_gateway,
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_schedule_gateway,
    get_current_user,
    get_engineering_context_engine,
    get_equipment_timeline_service,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_pm_occurrence_gateway,
    get_pm_schedule_gateway,
    get_pump_gateway,
    get_seal_gateway,
    get_seal_pump_compatibility_gateway,
    get_seal_stock_gateway,
    get_work_order_gateway,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity
from API.ltsa_knowledge_service import LTSAKnowledge
from API.recommendation_engine import Evidence, Recommendation

client = TestClient(app)

# MWO-LTSA-AUTH-001 -- every test in this file predates authorization and
# exercises router-to-gateway DELEGATION, not authorization itself (that
# is proven precisely, per-permission, in TESTS/test_auth_router.py).
# Overriding get_current_user here (autouse, whole file) keeps these ~60
# existing tests asserting exactly what they always asserted, rather than
# rewriting every one of them to carry a bearer token. A full-permission
# identity is used deliberately -- these tests must never be blocked by
# authorization, only by whatever behavior they were written to check.
_SUPERUSER_IDENTITY = AuthenticatedIdentity(
    user_id="test-superuser",
    email="test-superuser@tap.internal",
    organization_id="test-org-tap",
    organization_code="TAP",
    role="TAP_ADMIN",
    permissions=ROLE_PERMISSIONS["TAP_ADMIN"],
)


@pytest.fixture(autouse=True)
def _bypass_authorization_for_delegation_tests():
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    yield
    app.dependency_overrides.pop(get_current_user, None)


class FakePumpGateway:
    def __init__(self, list_response=None, detail_response=None):
        self.list_response = list_response
        self.detail_response = detail_response

    def list_pumps(self):
        return self.list_response

    def get_pump(self, tag_number):
        self.tag_number = tag_number
        return self.detail_response


class FakeWorkOrderGateway:
    def __init__(self, create_response=None, detail_response=None, list_response=None):
        self.create_response = create_response
        self.detail_response = detail_response
        self.list_response = list_response

    def create_work_order(self, payload):
        self.payload = payload
        return self.create_response

    def get_work_order(self, work_order_code):
        self.work_order_code = work_order_code
        return self.detail_response

    def list_work_orders(self):
        return self.list_response


class FakeMaintenanceHistoryGateway:
    def __init__(self, create_response=None, list_response=None, detail_response=None):
        self.create_response = create_response
        self.list_response = list_response
        self.detail_response = detail_response

    def create_maintenance_history(self, payload):
        self.payload = payload
        return self.create_response

    def list_maintenance_history(self):
        return self.list_response

    def get_maintenance_history(self, maintenance_record_code):
        self.maintenance_record_code = maintenance_record_code
        return self.detail_response


class FakePMScheduleGateway:
    def __init__(self, list_response=None, detail_response=None):
        self.list_response = list_response
        self.detail_response = detail_response

    def list_pm_schedules(self):
        return self.list_response

    def get_pm_schedule(self, pm_schedule_code):
        self.pm_schedule_code = pm_schedule_code
        return self.detail_response


class FakeCMReportGateway:
    def __init__(self, list_response=None, detail_response=None):
        self.list_response = list_response
        self.detail_response = detail_response

    def list_cm_reports(self):
        return self.list_response

    def get_cm_report(self, cm_report_code):
        self.cm_report_code = cm_report_code
        return self.detail_response


class FakeConditionMonitoringScheduleGateway:
    def __init__(self, list_response=None, detail_response=None):
        self.list_response = list_response
        self.detail_response = detail_response

    def list_condition_monitoring_schedules(self):
        return self.list_response

    def get_condition_monitoring_schedule(self, condition_monitoring_schedule_code):
        self.condition_monitoring_schedule_code = condition_monitoring_schedule_code
        return self.detail_response


class FakeConditionMonitoringReadingGateway:
    def __init__(self, list_response=None, detail_response=None):
        self.list_response = list_response
        self.detail_response = detail_response

    def list_condition_monitoring_readings(self):
        return self.list_response

    def get_condition_monitoring_reading(self, condition_monitoring_reading_code):
        self.condition_monitoring_reading_code = condition_monitoring_reading_code
        return self.detail_response


class FakePMOccurrenceGateway:
    def __init__(self, list_response=None, detail_response=None):
        self.list_response = list_response
        self.detail_response = detail_response

    def list_pm_occurrences(self):
        return self.list_response

    def get_pm_occurrence(self, pm_occurrence_code):
        self.pm_occurrence_code = pm_occurrence_code
        return self.detail_response


class FakeSealPumpCompatibilityGateway:
    def __init__(self, list_response=None):
        self.list_response = list_response

    def list_seal_pump_compatibilities(self):
        return self.list_response


class FakeSealStockGateway:
    def __init__(self, list_response=None):
        self.list_response = list_response

    def list_seal_stocks(self):
        return self.list_response


class FakeSealGateway:
    def __init__(self, list_response=None):
        self.list_response = list_response

    def list_seals(self):
        return self.list_response


class FakeLTSAKnowledgeService:
    def __init__(self, knowledge):
        self._knowledge = knowledge

    def build(self, tag_number):
        self.tag_number = tag_number
        return self._knowledge


class FakeEquipmentTimeline:
    def __init__(self, events=()):
        self.events = events


class FakeEquipmentTimelineService:
    def __init__(self, timeline=None, current_seal=None):
        self._timeline = timeline or FakeEquipmentTimeline()
        self._current_seal = current_seal

    def build(self, tag_number):
        return self._timeline

    # MWO-LTSA-ASSET360-MECHANICAL-SEAL-WIRING-001 -- GET .../knowledge now
    # also calls build_current_seal(); defaults to None (no authoritative
    # seal), matching every pre-existing test in this file that never
    # configures one.
    def build_current_seal(self, tag_number):
        return self._current_seal


class FakeEngineeringContextEngine:
    def __init__(self, summary=None):
        self._summary = summary if summary is not None else {}

    def build(self, tag_number):
        return self._summary


def test_health_reports_ok_when_dependencies_succeed():
    fake_pump_gateway = FakePumpGateway(list_response={"success": True, "data": []})
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        with patch("routers.health.get_organization", return_value={"company": {}}):
            response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["organization"] == "OK"
    assert body["database"] == "OK"
    assert body["n8n"] == "OK"
    assert "version" in body


def test_health_reports_unknown_and_down_when_dependencies_fail():
    fake_pump_gateway = FakePumpGateway()

    def raise_error(tag_number=None):
        raise ConnectionError("unreachable")

    fake_pump_gateway.list_pumps = raise_error
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        with patch("routers.health.get_organization", side_effect=ValueError("no Company artifact found")):
            response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["organization"] == "UNKNOWN"
    assert body["database"] == "DOWN"
    assert body["n8n"] == "DOWN"


def test_get_organization_delegates_to_organization_registry():
    org_payload = {"company": {"company": {"name": "CV Razzan"}}, "departments": [], "roles": []}

    with patch("routers.organization._get_organization", return_value=org_payload) as mock_fn:
        response = client.get("/organization")

    mock_fn.assert_called_once()
    assert response.status_code == 200
    assert response.json() == org_payload


def test_get_dashboard_delegates_to_organization_dashboard():
    dashboard_payload = {"organization": {"company_name": "CV Razzan"}}

    with patch("routers.dashboard._get_organization_dashboard", return_value=dashboard_payload) as mock_fn:
        response = client.get("/dashboard")

    mock_fn.assert_called_once()
    assert response.status_code == 200
    assert response.json() == dashboard_payload


def test_list_pumps_delegates_to_pump_gateway():
    list_response = {"success": True, "message": "ok", "count": 1, "data": [{"tag_number": "P-101"}]}
    fake_pump_gateway = FakePumpGateway(list_response=list_response)
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/pumps")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_get_pump_delegates_to_pump_gateway():
    detail_response = {"success": True, "message": "found", "data": {"tag_number": "P-101"}}
    fake_pump_gateway = FakePumpGateway(detail_response=detail_response)
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/pumps/P-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_pump_gateway.tag_number == "P-101"


def test_list_ltsa_pumps_delegates_to_pump_gateway():
    list_response = {"success": True, "message": "ok", "count": 1, "data": [{"tag_number": "P-101"}]}
    fake_pump_gateway = FakePumpGateway(list_response=list_response)
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/pumps")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_get_ltsa_pump_delegates_to_pump_gateway():
    detail_response = {"success": True, "message": "found", "data": {"tag_number": "P-101"}}
    fake_pump_gateway = FakePumpGateway(detail_response=detail_response)
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_pump_gateway.tag_number == "P-101"


def test_get_ltsa_pump_propagates_not_found_unchanged():
    not_found = {"success": False, "message": "Pump not found", "data": None}
    fake_pump_gateway = FakePumpGateway(detail_response=not_found)
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/pumps/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == not_found
    assert fake_pump_gateway.tag_number == "UNKNOWN"


def test_list_ltsa_pumps_includes_name_and_criticality():
    # WO-PUMP-002 (implements ADR-PUMP-001): proves the new columns survive
    # the full list round-trip through the already-existing, unmodified
    # /api/ltsa/pumps route and PumpGateway.
    list_response = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [{"tag_number": "P-101", "name": "Boiler Feedwater Pump 1A", "criticality": "HIGH"}],
    }
    fake_pump_gateway = FakePumpGateway(list_response=list_response)
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/pumps")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["name"] == "Boiler Feedwater Pump 1A"
    assert body["data"][0]["criticality"] == "HIGH"


def test_get_ltsa_pump_includes_name_and_criticality():
    detail_response = {
        "success": True,
        "message": "found",
        "data": {"tag_number": "P-101", "name": "Boiler Feedwater Pump 1A", "criticality": "HIGH"},
    }
    fake_pump_gateway = FakePumpGateway(detail_response=detail_response)
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["name"] == "Boiler Feedwater Pump 1A"
    assert body["data"]["criticality"] == "HIGH"
    assert fake_pump_gateway.tag_number == "P-101"


def test_get_ltsa_pump_open_work_orders_returns_openwo_count_and_list():
    list_response = {
        "success": True,
        "message": "Work orders listed",
        "count": 2,
        "data": [
            {"work_order_code": "WO-101", "asset_code": "P-101", "closed_at": None},
            {"work_order_code": "WO-102", "asset_code": "P-999", "closed_at": None},
        ],
    }
    fake_work_order_gateway = FakeWorkOrderGateway(list_response=list_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/workorders")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["tag_number"] == "P-101"
    assert body["openWO"] == 1
    assert body["data"] == [{"work_order_code": "WO-101", "asset_code": "P-101", "closed_at": None}]


def test_get_ltsa_pump_open_work_orders_returns_empty_when_none_open():
    list_response = {
        "success": True,
        "message": "Work orders listed",
        "count": 2,
        "data": [
            {"work_order_code": "WO-101", "asset_code": "P-101", "closed_at": "2026-07-01T00:00:00"},
            {"work_order_code": "WO-102", "asset_code": "P-999", "closed_at": None},
        ],
    }
    fake_work_order_gateway = FakeWorkOrderGateway(list_response=list_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/workorders")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["openWO"] == 0
    assert body["data"] == []


def test_get_ltsa_pump_open_work_orders_counts_multiple_matches():
    list_response = {
        "success": True,
        "message": "Work orders listed",
        "count": 3,
        "data": [
            {"work_order_code": "WO-101", "asset_code": "P-101", "closed_at": None},
            {"work_order_code": "WO-102", "asset_code": "P-101", "closed_at": None},
            {"work_order_code": "WO-103", "asset_code": "P-101", "closed_at": None},
        ],
    }
    fake_work_order_gateway = FakeWorkOrderGateway(list_response=list_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/workorders")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["openWO"] == 3
    assert len(body["data"]) == 3


def test_list_ltsa_maintenance_history_delegates_to_maintenance_history_gateway():
    list_response = {
        "success": True,
        "message": "Maintenance history listed",
        "count": 1,
        "data": [{"maintenance_record_code": "MH-101"}],
    }
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(list_response=list_response)
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway

    try:
        response = client.get("/api/ltsa/maintenance-history")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_get_ltsa_maintenance_history_delegates_to_maintenance_history_gateway():
    detail_response = {"success": True, "message": "found", "data": {"maintenance_record_code": "MH-101"}}
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(detail_response=detail_response)
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway

    try:
        response = client.get("/api/ltsa/maintenance-history/MH-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_maintenance_history_gateway.maintenance_record_code == "MH-101"


def test_get_ltsa_maintenance_history_propagates_not_found_unchanged():
    not_found = {"success": False, "message": "Maintenance history record not found", "data": None}
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(detail_response=not_found)
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway

    try:
        response = client.get("/api/ltsa/maintenance-history/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == not_found
    assert fake_maintenance_history_gateway.maintenance_record_code == "UNKNOWN"


def test_get_ltsa_pump_last_pm_returns_most_recent_pm_typed_record():
    maintenance_history_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [
            {
                "maintenance_record_code": "MH-101",
                "asset_code": "P-101",
                "work_order_code": "WO-101",
                "performed_at": "2026-07-01T00:00:00Z",
            }
        ],
    }
    work_order_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [{"work_order_code": "WO-101", "work_type": "PM"}],
    }
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(list_response=maintenance_history_list)
    fake_work_order_gateway = FakeWorkOrderGateway(list_response=work_order_list)
    fake_pm_occurrence_gateway = FakePMOccurrenceGateway(
        list_response={"success": True, "message": "ok", "count": 0, "data": []}
    )
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway
    app.dependency_overrides[get_pm_occurrence_gateway] = lambda: fake_pm_occurrence_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/last-pm")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["tag_number"] == "P-101"
    assert body["last_pm"]["source"] == "work_order"
    assert body["last_pm"]["record"]["maintenance_record_code"] == "MH-101"


def test_get_ltsa_pump_last_pm_returns_none_when_no_pm_records():
    maintenance_history_list = {"success": True, "message": "ok", "count": 0, "data": []}
    work_order_list = {"success": True, "message": "ok", "count": 0, "data": []}
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(list_response=maintenance_history_list)
    fake_work_order_gateway = FakeWorkOrderGateway(list_response=work_order_list)
    fake_pm_occurrence_gateway = FakePMOccurrenceGateway(
        list_response={"success": True, "message": "ok", "count": 0, "data": []}
    )
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway
    app.dependency_overrides[get_pm_occurrence_gateway] = lambda: fake_pm_occurrence_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/last-pm")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["last_pm"] is None


def test_get_ltsa_pump_last_pm_prefers_more_recent_pm_occurrence_over_work_order():
    # MWO-MAINTINT-001 / ADR-PM-OCCURRENCE-001: the canonical pm_occurrence
    # source wins when it is the more recent of the two candidates.
    maintenance_history_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [
            {
                "maintenance_record_code": "MH-101",
                "asset_code": "P-101",
                "work_order_code": "WO-101",
                "performed_at": "2026-06-01T00:00:00Z",
            }
        ],
    }
    work_order_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [{"work_order_code": "WO-101", "work_type": "PM"}],
    }
    pm_occurrence_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [
            {
                "pm_occurrence_code": "PM-OCC-101",
                "asset_code": "P-101",
                "occurrence_date": "2026-07-01T00:00:00Z",
            }
        ],
    }
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(list_response=maintenance_history_list)
    fake_work_order_gateway = FakeWorkOrderGateway(list_response=work_order_list)
    fake_pm_occurrence_gateway = FakePMOccurrenceGateway(list_response=pm_occurrence_list)
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway
    app.dependency_overrides[get_pm_occurrence_gateway] = lambda: fake_pm_occurrence_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/last-pm")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["last_pm"]["source"] == "pm_occurrence"
    assert body["last_pm"]["performed_at"] == "2026-07-01T00:00:00Z"
    assert body["last_pm"]["record"]["pm_occurrence_code"] == "PM-OCC-101"


def test_get_ltsa_pump_last_cm_delegates_to_cm_report_gateway():
    cm_report_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [
            {
                "cm_report_code": "CM-101",
                "asset_code": "P-101",
                "created_at": "2026-07-01T00:00:00Z",
            }
        ],
    }
    fake_cm_report_gateway = FakeCMReportGateway(list_response=cm_report_list)
    app.dependency_overrides[get_cm_report_gateway] = lambda: fake_cm_report_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/last-cm")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["tag_number"] == "P-101"
    assert body["last_cm"]["cm_report_code"] == "CM-101"


def test_get_ltsa_pump_last_cm_returns_none_when_no_reports():
    cm_report_list = {"success": True, "message": "ok", "count": 0, "data": []}
    fake_cm_report_gateway = FakeCMReportGateway(list_response=cm_report_list)
    app.dependency_overrides[get_cm_report_gateway] = lambda: fake_cm_report_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/last-cm")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["last_cm"] is None


def test_get_ltsa_pump_condition_monitoring_flag_delegates_to_gateway():
    condition_monitoring_reading_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [
            {
                "condition_monitoring_reading_code": "CMON-101",
                "asset_code": "P-101",
                "reading_date": "2026-07-01T00:00:00Z",
                "mechanical_seal_leak_de": True,
            }
        ],
    }
    fake_gateway = FakeConditionMonitoringReadingGateway(list_response=condition_monitoring_reading_list)
    app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/condition-monitoring-flag")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["tag_number"] == "P-101"
    # The route does not pin `today`, so this only proves delegation and
    # response shape -- window-boundary behavior is covered at the
    # maintenance_intelligence_service unit-test level, where `today` can
    # be pinned deterministically.
    assert "flagged" in body
    assert "window_days" in body


def test_get_ltsa_pump_condition_monitoring_flag_false_when_no_readings():
    condition_monitoring_reading_list = {"success": True, "message": "ok", "count": 0, "data": []}
    fake_gateway = FakeConditionMonitoringReadingGateway(list_response=condition_monitoring_reading_list)
    app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/condition-monitoring-flag")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["flagged"] is False


def test_get_ltsa_pump_spare_parts_returns_compatible_seals_with_stock():
    compatibility_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [{"seal_code": "SC-001", "pump_tag_number": "P-101"}],
    }
    stock_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [{"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}],
    }
    seal_list = {
        "success": True,
        "message": "ok",
        "count": 1,
        "data": [{"seal_code": "SC-001", "seal_name": "John Crane Type 21"}],
    }
    fake_compatibility_gateway = FakeSealPumpCompatibilityGateway(list_response=compatibility_list)
    fake_stock_gateway = FakeSealStockGateway(list_response=stock_list)
    fake_seal_gateway = FakeSealGateway(list_response=seal_list)
    app.dependency_overrides[get_seal_pump_compatibility_gateway] = lambda: fake_compatibility_gateway
    app.dependency_overrides[get_seal_stock_gateway] = lambda: fake_stock_gateway
    app.dependency_overrides[get_seal_gateway] = lambda: fake_seal_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-101/spare-parts")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["tag_number"] == "P-101"
    assert body["spare_parts"] == [
        {
            "seal_code": "SC-001",
            "part_name": "John Crane Type 21",
            "quantity_on_hand": 4,
            "reorder_point": 2,
            "location": "Warehouse A",
        }
    ]


def test_get_ltsa_pump_spare_parts_returns_empty_list_when_no_compatible_seals():
    empty_list = {"success": True, "message": "ok", "count": 0, "data": []}
    fake_compatibility_gateway = FakeSealPumpCompatibilityGateway(list_response=empty_list)
    fake_stock_gateway = FakeSealStockGateway(list_response=empty_list)
    fake_seal_gateway = FakeSealGateway(list_response=empty_list)
    app.dependency_overrides[get_seal_pump_compatibility_gateway] = lambda: fake_compatibility_gateway
    app.dependency_overrides[get_seal_stock_gateway] = lambda: fake_stock_gateway
    app.dependency_overrides[get_seal_gateway] = lambda: fake_seal_gateway

    try:
        response = client.get("/api/ltsa/pumps/P-999/spare-parts")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["spare_parts"] == []


def test_list_ltsa_pm_schedules_delegates_to_pm_schedule_gateway():
    list_response = {
        "success": True,
        "message": "PM schedules listed",
        "count": 1,
        "data": [{"pm_schedule_code": "PM-101"}],
    }
    fake_pm_schedule_gateway = FakePMScheduleGateway(list_response=list_response)
    app.dependency_overrides[get_pm_schedule_gateway] = lambda: fake_pm_schedule_gateway

    try:
        response = client.get("/api/ltsa/pm-schedules")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_get_ltsa_pm_schedule_delegates_to_pm_schedule_gateway():
    detail_response = {"success": True, "message": "found", "data": {"pm_schedule_code": "PM-101"}}
    fake_pm_schedule_gateway = FakePMScheduleGateway(detail_response=detail_response)
    app.dependency_overrides[get_pm_schedule_gateway] = lambda: fake_pm_schedule_gateway

    try:
        response = client.get("/api/ltsa/pm-schedules/PM-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_pm_schedule_gateway.pm_schedule_code == "PM-101"


def test_get_ltsa_pm_schedule_propagates_not_found_unchanged():
    not_found = {"success": False, "message": "PM schedule not found", "data": None}
    fake_pm_schedule_gateway = FakePMScheduleGateway(detail_response=not_found)
    app.dependency_overrides[get_pm_schedule_gateway] = lambda: fake_pm_schedule_gateway

    try:
        response = client.get("/api/ltsa/pm-schedules/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == not_found
    assert fake_pm_schedule_gateway.pm_schedule_code == "UNKNOWN"


def test_list_ltsa_pm_occurrences_delegates_to_pm_occurrence_gateway():
    list_response = {
        "success": True,
        "message": "PM occurrence list retrieved",
        "count": 1,
        "data": [{"pm_occurrence_code": "PM-OCC-101"}],
    }
    fake_gateway = FakePMOccurrenceGateway(list_response=list_response)
    app.dependency_overrides[get_pm_occurrence_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/pm-occurrences")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_get_ltsa_pm_occurrence_delegates_to_pm_occurrence_gateway():
    detail_response = {"success": True, "message": "found", "data": {"pm_occurrence_code": "PM-OCC-101"}}
    fake_gateway = FakePMOccurrenceGateway(detail_response=detail_response)
    app.dependency_overrides[get_pm_occurrence_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/pm-occurrences/PM-OCC-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_gateway.pm_occurrence_code == "PM-OCC-101"


def test_get_ltsa_pm_occurrence_propagates_not_found_unchanged():
    not_found = {"success": False, "message": "PM occurrence not found", "data": None}
    fake_gateway = FakePMOccurrenceGateway(detail_response=not_found)
    app.dependency_overrides[get_pm_occurrence_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/pm-occurrences/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == not_found
    assert fake_gateway.pm_occurrence_code == "UNKNOWN"


def test_list_ltsa_cm_reports_delegates_to_cm_report_gateway():
    list_response = {
        "success": True,
        "message": "CM report list retrieved",
        "count": 1,
        "data": [{"cm_report_code": "CM-101"}],
    }
    fake_cm_report_gateway = FakeCMReportGateway(list_response=list_response)
    app.dependency_overrides[get_cm_report_gateway] = lambda: fake_cm_report_gateway

    try:
        response = client.get("/api/ltsa/cm-reports")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_get_ltsa_cm_report_delegates_to_cm_report_gateway():
    detail_response = {"success": True, "message": "found", "data": {"cm_report_code": "CM-101"}}
    fake_cm_report_gateway = FakeCMReportGateway(detail_response=detail_response)
    app.dependency_overrides[get_cm_report_gateway] = lambda: fake_cm_report_gateway

    try:
        response = client.get("/api/ltsa/cm-reports/CM-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_cm_report_gateway.cm_report_code == "CM-101"


def test_get_ltsa_cm_report_propagates_not_found_unchanged():
    not_found = {"success": False, "message": "CM report not found", "data": None}
    fake_cm_report_gateway = FakeCMReportGateway(detail_response=not_found)
    app.dependency_overrides[get_cm_report_gateway] = lambda: fake_cm_report_gateway

    try:
        response = client.get("/api/ltsa/cm-reports/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == not_found
    assert fake_cm_report_gateway.cm_report_code == "UNKNOWN"


def test_list_ltsa_condition_monitoring_schedules_delegates_to_condition_monitoring_schedule_gateway():
    list_response = {
        "success": True,
        "message": "Condition Monitoring schedule list retrieved",
        "count": 1,
        "data": [{"condition_monitoring_schedule_code": "CMON-SCHED-101"}],
    }
    fake_gateway = FakeConditionMonitoringScheduleGateway(list_response=list_response)
    app.dependency_overrides[get_condition_monitoring_schedule_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/condition-monitoring-schedules")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_get_ltsa_condition_monitoring_schedule_delegates_to_condition_monitoring_schedule_gateway():
    detail_response = {
        "success": True,
        "message": "found",
        "data": {"condition_monitoring_schedule_code": "CMON-SCHED-101"},
    }
    fake_gateway = FakeConditionMonitoringScheduleGateway(detail_response=detail_response)
    app.dependency_overrides[get_condition_monitoring_schedule_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/condition-monitoring-schedules/CMON-SCHED-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_gateway.condition_monitoring_schedule_code == "CMON-SCHED-101"


def test_get_ltsa_condition_monitoring_schedule_propagates_not_found_unchanged():
    not_found = {"success": False, "message": "Condition Monitoring schedule not found", "data": None}
    fake_gateway = FakeConditionMonitoringScheduleGateway(detail_response=not_found)
    app.dependency_overrides[get_condition_monitoring_schedule_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/condition-monitoring-schedules/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == not_found
    assert fake_gateway.condition_monitoring_schedule_code == "UNKNOWN"


def test_list_ltsa_condition_monitoring_readings_delegates_to_condition_monitoring_reading_gateway():
    list_response = {
        "success": True,
        "message": "Condition Monitoring reading list retrieved",
        "count": 1,
        "data": [{"condition_monitoring_reading_code": "CMON-READ-101"}],
    }
    fake_gateway = FakeConditionMonitoringReadingGateway(list_response=list_response)
    app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/condition-monitoring-readings")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_get_ltsa_condition_monitoring_reading_delegates_to_condition_monitoring_reading_gateway():
    detail_response = {
        "success": True,
        "message": "found",
        "data": {"condition_monitoring_reading_code": "CMON-READ-101"},
    }
    fake_gateway = FakeConditionMonitoringReadingGateway(detail_response=detail_response)
    app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/condition-monitoring-readings/CMON-READ-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_gateway.condition_monitoring_reading_code == "CMON-READ-101"


def test_get_ltsa_condition_monitoring_reading_propagates_not_found_unchanged():
    not_found = {"success": False, "message": "Condition Monitoring reading not found", "data": None}
    fake_gateway = FakeConditionMonitoringReadingGateway(detail_response=not_found)
    app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: fake_gateway

    try:
        response = client.get("/api/ltsa/condition-monitoring-readings/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == not_found
    assert fake_gateway.condition_monitoring_reading_code == "UNKNOWN"


def test_create_work_order_delegates_to_work_order_gateway():
    create_response = {"success": True, "message": "created", "data": {"work_order_code": "WO-101"}}
    fake_work_order_gateway = FakeWorkOrderGateway(create_response=create_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.post(
            "/work-orders",
            json={"work_order_code": "WO-101", "description": "Bearing replacement"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == create_response
    assert fake_work_order_gateway.payload["work_order_code"] == "WO-101"
    assert fake_work_order_gateway.payload["description"] == "Bearing replacement"


def test_get_work_order_delegates_to_work_order_gateway():
    detail_response = {"success": True, "message": "found", "data": {"work_order_code": "WO-101"}}
    fake_work_order_gateway = FakeWorkOrderGateway(detail_response=detail_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.get("/work-orders/WO-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_work_order_gateway.work_order_code == "WO-101"


def test_list_ltsa_work_orders_delegates_to_work_order_gateway():
    list_response = {
        "success": True,
        "message": "Work orders listed",
        "count": 2,
        "data": [{"work_order_code": "WO-101"}, {"work_order_code": "WO-102"}],
    }
    fake_work_order_gateway = FakeWorkOrderGateway(list_response=list_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.get("/api/ltsa/workorders")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == list_response


def test_create_ltsa_work_order_forwards_title_work_type_due_date():
    # WO-BE-004 (implements ADR-WO-003): proves the updated
    # WorkOrderCreateRequest actually accepts and forwards the three new
    # optional fields through to the gateway payload, not just that the
    # gateway itself is payload-agnostic (covered separately in
    # test_work_order_gateway.py).
    create_response = {"success": True, "message": "created", "data": {"work_order_code": "WO-101"}}
    fake_work_order_gateway = FakeWorkOrderGateway(create_response=create_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.post(
            "/api/ltsa/workorders",
            json={
                "work_order_code": "WO-101",
                "description": "Bearing replacement",
                "title": "Seal replacement",
                "work_type": "CM",
                "due_date": "2026-08-01",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == create_response
    assert fake_work_order_gateway.payload["title"] == "Seal replacement"
    assert fake_work_order_gateway.payload["work_type"] == "CM"
    assert fake_work_order_gateway.payload["due_date"] == "2026-08-01"


def test_create_ltsa_work_order_omits_title_work_type_due_date_when_not_sent():
    # Backward compatibility: an existing caller that never sends the three
    # new fields must keep working unchanged -- they come through as None,
    # matching the nullable columns, not a validation error.
    create_response = {"success": True, "message": "created", "data": {"work_order_code": "WO-102"}}
    fake_work_order_gateway = FakeWorkOrderGateway(create_response=create_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.post(
            "/api/ltsa/workorders",
            json={"work_order_code": "WO-102", "description": "Bearing replacement"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert fake_work_order_gateway.payload["title"] is None
    assert fake_work_order_gateway.payload["work_type"] is None
    assert fake_work_order_gateway.payload["due_date"] is None


def test_get_ltsa_work_order_delegates_to_work_order_gateway():
    detail_response = {"success": True, "message": "found", "data": {"work_order_code": "WO-101"}}
    fake_work_order_gateway = FakeWorkOrderGateway(detail_response=detail_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.get("/api/ltsa/workorders/WO-101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == detail_response
    assert fake_work_order_gateway.work_order_code == "WO-101"


def test_create_ltsa_work_order_delegates_to_work_order_gateway():
    create_response = {"success": True, "message": "created", "data": {"work_order_code": "WO-101"}}
    fake_work_order_gateway = FakeWorkOrderGateway(create_response=create_response)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway

    try:
        response = client.post(
            "/api/ltsa/workorders",
            json={"work_order_code": "WO-101", "description": "Bearing replacement"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == create_response
    assert fake_work_order_gateway.payload["work_order_code"] == "WO-101"
    assert fake_work_order_gateway.payload["description"] == "Bearing replacement"


def test_get_ltsa_work_order_timeline_filters_by_work_order_code():
    list_response = {
        "success": True,
        "message": "Maintenance history listed",
        "count": 3,
        "data": [
            {"maintenance_record_code": "MH-101", "work_order_code": "WO-101", "action_taken": "Inspected"},
            {"maintenance_record_code": "MH-102", "work_order_code": "WO-102", "action_taken": "Replaced seal"},
            {"maintenance_record_code": "MH-103", "work_order_code": "WO-101", "action_taken": "Closed"},
        ],
    }
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(list_response=list_response)
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway

    try:
        response = client.get("/api/ltsa/workorders/WO-101/timeline")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["count"] == 2
    assert body["data"] == [
        {"maintenance_record_code": "MH-101", "work_order_code": "WO-101", "action_taken": "Inspected"},
        {"maintenance_record_code": "MH-103", "work_order_code": "WO-101", "action_taken": "Closed"},
    ]


def test_get_ltsa_work_order_timeline_returns_empty_data_when_no_records_match():
    list_response = {
        "success": True,
        "message": "Maintenance history listed",
        "count": 1,
        "data": [{"maintenance_record_code": "MH-102", "work_order_code": "WO-102"}],
    }
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(list_response=list_response)
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway

    try:
        response = client.get("/api/ltsa/workorders/WO-999/timeline")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["count"] == 0
    assert body["data"] == []


def test_get_ltsa_work_order_timeline_propagates_gateway_failure_unchanged():
    failure_response = {"success": False, "message": "Maintenance history API unavailable", "data": None}
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(list_response=failure_response)
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway

    try:
        response = client.get("/api/ltsa/workorders/WO-101/timeline")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == failure_response


def test_get_ltsa_work_order_asset_resolves_area_for_a_matching_pump():
    work_order_detail = {
        "success": True,
        "message": "found",
        "data": {"work_order_code": "WO-101", "asset_code": "P-101", "asset_type": "PUMP"},
    }
    pump_detail = {
        "success": True,
        "message": "found",
        "data": {"tag_number": "P-101", "area": "Unit 1"},
    }
    fake_work_order_gateway = FakeWorkOrderGateway(detail_response=work_order_detail)
    fake_pump_gateway = FakePumpGateway(detail_response=pump_detail)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/workorders/WO-101/asset")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["asset_code"] == "P-101"
    assert body["asset_type"] == "PUMP"
    assert body["area"] == "Unit 1"
    assert fake_pump_gateway.tag_number == "P-101"


def test_get_ltsa_work_order_asset_reports_unknown_asset_when_pump_not_found():
    work_order_detail = {
        "success": True,
        "message": "found",
        "data": {"work_order_code": "WO-101", "asset_code": "P-999", "asset_type": "PUMP"},
    }
    pump_not_found = {"success": False, "message": "Pump not found", "data": None}
    fake_work_order_gateway = FakeWorkOrderGateway(detail_response=work_order_detail)
    fake_pump_gateway = FakePumpGateway(detail_response=pump_not_found)
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/workorders/WO-101/asset")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["asset_code"] == "P-999"
    assert body["asset_type"] == "PUMP"
    assert body["area"] is None


def test_get_ltsa_work_order_asset_reports_unsupported_asset_type():
    work_order_detail = {
        "success": True,
        "message": "found",
        "data": {"work_order_code": "WO-102", "asset_code": "SEAL-1", "asset_type": "SEAL"},
    }
    fake_work_order_gateway = FakeWorkOrderGateway(detail_response=work_order_detail)
    fake_pump_gateway = FakePumpGateway()
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/workorders/WO-102/asset")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["asset_code"] == "SEAL-1"
    assert body["asset_type"] == "SEAL"
    assert body["area"] is None


def test_get_ltsa_work_order_asset_propagates_work_order_not_found_unchanged():
    not_found = {"success": False, "message": "Work order not found", "data": None}
    fake_work_order_gateway = FakeWorkOrderGateway(detail_response=not_found)
    fake_pump_gateway = FakePumpGateway()
    app.dependency_overrides[get_work_order_gateway] = lambda: fake_work_order_gateway
    app.dependency_overrides[get_pump_gateway] = lambda: fake_pump_gateway

    try:
        response = client.get("/api/ltsa/workorders/UNKNOWN/asset")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == not_found


def test_create_maintenance_delegates_to_maintenance_history_gateway():
    create_response = {
        "success": True,
        "message": "created",
        "data": {"maintenance_record_code": "MH-101"},
    }
    fake_maintenance_history_gateway = FakeMaintenanceHistoryGateway(create_response=create_response)
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: fake_maintenance_history_gateway

    try:
        response = client.post(
            "/maintenance",
            json={"maintenance_record_code": "MH-101", "action_taken": "Replaced bearing"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == create_response
    assert fake_maintenance_history_gateway.payload["maintenance_record_code"] == "MH-101"


def test_copilot_summary_delegates_to_maintenance_copilot():
    summary_payload = {"message": "1 pump(s) tracked.", "data": {}}

    with patch(
        "routers.copilot._summarize_maintenance_situation", return_value=summary_payload
    ) as mock_fn:
        response = client.get("/copilot/summary")

    mock_fn.assert_called_once()
    assert response.status_code == 200
    assert response.json() == summary_payload


def _knowledge_for_route_test(recommendation=(), drawings=None):
    return LTSAKnowledge(
        tag_number="P-101",
        pump={"tag_number": "P-101"},
        seal=[],
        inventory=[],
        pm_history=[],
        cm_history=[],
        breakdown_history=[],
        drawings=drawings if drawings is not None else [],
        recommendation=recommendation,
        pm_schedules=[],
        condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )


def test_get_ltsa_pump_knowledge_serializes_populated_drawing_list():
    # MWO-LTSA-033: proves the router passes LTSAKnowledgeService's real
    # drawings list through to the Knowledge API response unchanged --
    # reusing the same plain-passthrough pattern already used for
    # seal/inventory/pm/cm/breakdown (drawings entries are already plain
    # dicts, not dataclasses, so no asdict() step is needed here).
    drawings = [
        {
            "drawing_id": "DOC-001",
            "title": "SC-001 GA Drawing",
            "document_number": "DWG-4471",
            "revision": "B",
            "status": "APPROVED",
            "file_name": "sc-001-ga.pdf",
            "uploaded_at": "2026-05-01T00:00:00Z",
        }
    ]
    fake_knowledge_service = FakeLTSAKnowledgeService(_knowledge_for_route_test(drawings=drawings))
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: fake_knowledge_service
    app.dependency_overrides[get_equipment_timeline_service] = lambda: FakeEquipmentTimelineService()
    app.dependency_overrides[get_engineering_context_engine] = lambda: FakeEngineeringContextEngine()

    try:
        response = client.get("/api/ltsa/pumps/P-101/knowledge")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["drawings"] == drawings


def test_get_ltsa_pump_knowledge_serializes_empty_drawing_list():
    fake_knowledge_service = FakeLTSAKnowledgeService(_knowledge_for_route_test(drawings=[]))
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: fake_knowledge_service
    app.dependency_overrides[get_equipment_timeline_service] = lambda: FakeEquipmentTimelineService()
    app.dependency_overrides[get_engineering_context_engine] = lambda: FakeEngineeringContextEngine()

    try:
        response = client.get("/api/ltsa/pumps/P-101/knowledge")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["drawings"] == []


def test_get_ltsa_pump_knowledge_serializes_populated_recommendation_list():
    # MWO-LTSA-032C: proves the router serializes real Recommendation
    # dataclasses (including nested Evidence) the same way it already
    # serializes Timeline events -- dataclasses.asdict() per item.
    evidence = (Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL"),)
    rec = Recommendation(
        id="REC_CRITICAL_CM:P-101",
        rule_code="REC_CRITICAL_CM",
        priority=100,
        category="INSPECTION",
        title="Immediate Inspection",
        description="An open Corrective Maintenance report with critical or major severity was found.",
        evidence=evidence,
        confidence=1.0,
        action="Dispatch a technician for immediate inspection.",
    )
    fake_knowledge_service = FakeLTSAKnowledgeService(_knowledge_for_route_test(recommendation=(rec,)))
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: fake_knowledge_service
    app.dependency_overrides[get_equipment_timeline_service] = lambda: FakeEquipmentTimelineService()
    app.dependency_overrides[get_engineering_context_engine] = lambda: FakeEngineeringContextEngine()

    try:
        response = client.get("/api/ltsa/pumps/P-101/knowledge")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["recommendation"] == [
        {
            "id": "REC_CRITICAL_CM:P-101",
            "rule_code": "REC_CRITICAL_CM",
            "priority": 100,
            "category": "INSPECTION",
            "title": "Immediate Inspection",
            "description": "An open Corrective Maintenance report with critical or major severity was found.",
            "evidence": [
                {"source": "CMReport", "reference": "CM-1", "field": "severity", "value": "CRITICAL"},
            ],
            "confidence": 1.0,
            "action": "Dispatch a technician for immediate inspection.",
        }
    ]
    assert fake_knowledge_service.tag_number == "P-101"


def test_get_ltsa_pump_knowledge_serializes_empty_recommendation_list():
    fake_knowledge_service = FakeLTSAKnowledgeService(_knowledge_for_route_test(recommendation=()))
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: fake_knowledge_service
    app.dependency_overrides[get_equipment_timeline_service] = lambda: FakeEquipmentTimelineService()
    app.dependency_overrides[get_engineering_context_engine] = lambda: FakeEngineeringContextEngine()

    try:
        response = client.get("/api/ltsa/pumps/P-101/knowledge")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["recommendation"] == []


def test_get_ltsa_pump_knowledge_preserves_priority_confidence_and_evidence_across_multiple_recommendations():
    rec_high = Recommendation(
        id="REC_NO_STOCK:P-101", rule_code="REC_NO_STOCK", priority=90, category="SPARE_PART",
        title="Procurement Required", description="d",
        evidence=(Evidence(source="SealStock", reference="SC-001", field="quantity_on_hand", value="0"),),
        confidence=1.0, action="a",
    )
    rec_medium = Recommendation(
        id="REC_PM_OVERDUE:P-101", rule_code="REC_PM_OVERDUE", priority=70, category="MAINTENANCE",
        title="Schedule PM", description="d", evidence=(), confidence=0.6, action="a",
    )
    fake_knowledge_service = FakeLTSAKnowledgeService(
        _knowledge_for_route_test(recommendation=(rec_high, rec_medium))
    )
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: fake_knowledge_service
    app.dependency_overrides[get_equipment_timeline_service] = lambda: FakeEquipmentTimelineService()
    app.dependency_overrides[get_engineering_context_engine] = lambda: FakeEngineeringContextEngine()

    try:
        response = client.get("/api/ltsa/pumps/P-101/knowledge")
    finally:
        app.dependency_overrides.clear()

    recommendations = response.json()["data"]["recommendation"]
    assert [r["priority"] for r in recommendations] == [90, 70]
    assert [r["confidence"] for r in recommendations] == [1.0, 0.6]
    assert recommendations[0]["evidence"] == [
        {"source": "SealStock", "reference": "SC-001", "field": "quantity_on_hand", "value": "0"}
    ]
    assert recommendations[1]["evidence"] == []


def test_get_ltsa_pump_knowledge_recommendation_is_none_safe_for_directly_constructed_knowledge():
    # LTSAKnowledge.recommendation is typed `Any` -- a directly-constructed
    # instance (as several existing tests build) can still legitimately
    # pass None, and the router must not crash on it.
    fake_knowledge_service = FakeLTSAKnowledgeService(_knowledge_for_route_test(recommendation=None))
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: fake_knowledge_service
    app.dependency_overrides[get_equipment_timeline_service] = lambda: FakeEquipmentTimelineService()
    app.dependency_overrides[get_engineering_context_engine] = lambda: FakeEngineeringContextEngine()

    try:
        response = client.get("/api/ltsa/pumps/P-101/knowledge")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["recommendation"] is None


def test_docs_and_openapi_are_available():
    docs_response = client.get("/docs")
    openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert openapi_response.status_code == 200

    paths = openapi_response.json()["paths"]
    for path in (
        "/health",
        "/api/auth/login",
        "/api/auth/me",
        "/organization",
        "/dashboard",
        "/pumps",
        "/pumps/{tag}",
        "/api/ltsa/pumps",
        "/api/ltsa/pumps/{tag}",
        "/api/ltsa/pumps/{tag}/workorders",
        "/api/ltsa/pumps/{tag}/last-pm",
        "/api/ltsa/pumps/{tag}/last-cm",
        "/api/ltsa/pumps/{tag}/condition-monitoring-flag",
        "/api/ltsa/pumps/{tag}/spare-parts",
        "/api/ltsa/pumps/{tag}/knowledge",
        "/api/ltsa/pumps/{tag}/lifecycle",
        "/api/ltsa/maintenance-history",
        "/api/ltsa/maintenance-history/{code}",
        "/api/ltsa/pm-schedules",
        "/api/ltsa/pm-schedules/{code}",
        "/api/ltsa/pm-occurrences",
        "/api/ltsa/pm-occurrences/{code}",
        "/api/ltsa/cm-reports",
        "/api/ltsa/cm-reports/{code}",
        "/api/ltsa/condition-monitoring-schedules",
        "/api/ltsa/condition-monitoring-schedules/{code}",
        "/api/ltsa/condition-monitoring-readings",
        "/api/ltsa/condition-monitoring-readings/{code}",
        "/work-orders",
        "/work-orders/{id}",
        "/api/ltsa/workorders",
        "/api/ltsa/workorders/{id}",
        "/api/ltsa/workorders/{id}/timeline",
        "/api/ltsa/workorders/{id}/asset",
        "/maintenance",
        "/copilot/summary",
    ):
        assert path in paths

    # MWO-LTSA-AUTH-001A -- engineering_ai is deliberately NOT wired: its
    # orchestrator is never configured outside its own test file (see
    # routers/engineering_ai.py), so wiring it would expose a 500-on-
    # every-request endpoint rather than close a real gap. This asserts
    # that omission is intentional and still true, not a silent gap.
    assert "/api/ltsa/engineering-ai" not in paths
