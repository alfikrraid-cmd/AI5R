import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from fastapi.testclient import TestClient

from main import app
from dependencies import (
    get_maintenance_history_gateway,
    get_pump_gateway,
    get_work_order_gateway,
)

client = TestClient(app)


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
    def __init__(self, create_response=None, detail_response=None):
        self.create_response = create_response
        self.detail_response = detail_response

    def create_work_order(self, payload):
        self.payload = payload
        return self.create_response

    def get_work_order(self, work_order_code):
        self.work_order_code = work_order_code
        return self.detail_response


class FakeMaintenanceHistoryGateway:
    def __init__(self, create_response=None):
        self.create_response = create_response

    def create_maintenance_history(self, payload):
        self.payload = payload
        return self.create_response


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


def test_docs_and_openapi_are_available():
    docs_response = client.get("/docs")
    openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert openapi_response.status_code == 200

    paths = openapi_response.json()["paths"]
    for path in (
        "/health",
        "/organization",
        "/dashboard",
        "/pumps",
        "/pumps/{tag}",
        "/work-orders",
        "/work-orders/{id}",
        "/maintenance",
        "/copilot/summary",
    ):
        assert path in paths
