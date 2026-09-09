import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app
from dependencies import get_current_user, get_ltsa_analytics_service
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity

client = TestClient(app)

_SUPERUSER_IDENTITY = AuthenticatedIdentity(
    user_id="test-superuser",
    email="test-superuser@tap.internal",
    organization_id="test-org-tap",
    organization_code="TAP",
    role="TAP_ADMIN",
    permissions=ROLE_PERMISSIONS["TAP_ADMIN"],
)

_UNAUTHORIZED_IDENTITY = AuthenticatedIdentity(
    user_id="test-no-perm",
    email="no-perm@tap.internal",
    organization_id="test-org-tap",
    organization_code="TAP",
    role="READONLY",
    permissions=frozenset(),
)


class FakeLTSAAnalyticsService:
    def __init__(self):
        self.last_executive_kwargs = {}
        self.last_seal_kwargs = {}
        self.last_material_kwargs = {}
        self.last_effectiveness_kwargs = {}
        self.last_filter_kwargs = {}

    def get_filter_options(self, *, scope=None):
        self.last_filter_kwargs = {"scope": scope}
        return {
            "areas": [{"area": "HCC", "pump_count": 82}],
            "pumps": [{"tag_number": "220-P-3A", "area": "HOC", "pump_type": "BB"}],
            "date_range": {"min_date": "2026-07-01", "max_date": "2026-07-31"},
        }

    def get_executive_analytics(self, **kwargs):
        self.last_executive_kwargs = kwargs
        return {
            "kpis": {
                "total_pumps": 244,
                "active_pumps": None,  # Unknown != Zero
                "monitored_pumps": 211,
                "pm_executed_count": 53,
                "pm_done_count": 53,
                "pm_scheduled_count": None,
                "pm_compliance_percent": None,
                "confirmed_seal_leaks": 52,
                "de_leaks": 45,
                "nde_leaks": 9,
                "breakdown_count": 0,
                "fleet_mtbf_days": None,  # Unknown != Zero
                "fleet_mttr_hours": None,  # Unknown != Zero
                "fleet_availability": None,  # Unknown != Zero
            },
            "trends": {
                "daily": [{"date": "2026-07-01", "pm_count": 0, "cmon_readings": 25, "seal_leaks": 5}],
            },
            "area_breakdown": [
                {"area": "HCC", "pump_count": 82, "pm_count": 19, "cmon_readings": 215, "seal_leaks": 22}
            ],
            "top_bad_actors": [
                {
                    "pump_tag": "220-P-3A",
                    "area": "HOC",
                    "pump_type": "BB",
                    "api_plan": "22/62",
                    "leak_count": 3,
                    "cmon_readings": 3,
                    "pm_count": 0,
                    "latest_leak_date": "2026-07-21",
                }
            ],
            "historical_findings": [],
        }

    def get_seal_analytics(self, **kwargs):
        self.last_seal_kwargs = kwargs
        return {
            "summary": {
                "seal_replacements_count": None,
                "mtbsr_days": None,
                "total_registered_seals": 0,
                "total_stock_units": 0,
                "has_replacement_data": False,
                "has_stock_data": False,
            },
            "leaks_by_pump_type": [{"pump_type": "BB", "total_readings": 150, "leak_count": 22}],
            "leaks_by_api_plan": [{"api_plan": "11/61", "total_readings": 80, "leak_count": 12}],
        }

    def get_material_analytics(self, **kwargs):
        self.last_material_kwargs = kwargs
        return {
            "has_data": False,
            "summary": {
                "total_items_consumed": None,
                "total_cost": None,
            },
            "top_consumed_materials": [],
            "message": "Material and spare parts consumption data not yet ingested in current contract period.",
        }

    def get_maintenance_effectiveness(self, **kwargs):
        self.last_effectiveness_kwargs = kwargs
        return {
            "metrics": {
                "pm_executed": 53,
                "confirmed_leaks": 52,
                "pm_to_leak_ratio": 1.02,
                "proactive_ratio_percent": 50.5,
                "first_time_fix_rate": None,
                "mean_time_to_respond_days": None,
            },
            "area_effectiveness": [
                {"area": "HCC", "pm_count": 19, "leak_count": 22, "proactive_percent": 46.3}
            ],
        }


@pytest.fixture(autouse=True)
def _clean_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_analytics_endpoints_require_auth():
    response = client.get("/api/ltsa/analytics/executive")
    assert response.status_code == 401


def test_analytics_endpoints_require_permission():
    app.dependency_overrides[get_current_user] = lambda: _UNAUTHORIZED_IDENTITY
    response = client.get("/api/ltsa/analytics/executive")
    assert response.status_code == 403
    assert "Missing permission: pump.read" in response.json()["detail"]


def test_get_analytics_filters():
    fake = FakeLTSAAnalyticsService()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_ltsa_analytics_service] = lambda: fake

    response = client.get("/api/ltsa/analytics/filters")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "areas" in data
    assert "pumps" in data
    assert "date_range" in data


def test_get_executive_analytics_success_and_unknown_policy():
    fake = FakeLTSAAnalyticsService()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_ltsa_analytics_service] = lambda: fake

    response = client.get(
        "/api/ltsa/analytics/executive?contract_area=HCC&area=HCC&pump_tag=101-P-10A&start_date=2026-07-01&end_date=2026-07-31"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]

    # Verify query parameter forwarding
    assert fake.last_executive_kwargs["contract_area"] == "HCC"
    assert fake.last_executive_kwargs["area"] == "HCC"
    assert fake.last_executive_kwargs["pump_tag"] == "101-P-10A"
    assert fake.last_executive_kwargs["start_date"] == "2026-07-01"
    assert fake.last_executive_kwargs["end_date"] == "2026-07-31"

    # Verify UNKNOWN != ZERO policy
    kpis = data["kpis"]
    assert kpis["fleet_mtbf_days"] is None
    assert kpis["fleet_mttr_hours"] is None
    assert kpis["fleet_availability"] is None
    assert kpis["active_pumps"] is None
    assert kpis["confirmed_seal_leaks"] == 52
    assert kpis["pm_executed_count"] == 53


def test_get_seal_analytics():
    fake = FakeLTSAAnalyticsService()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_ltsa_analytics_service] = lambda: fake

    response = client.get("/api/ltsa/analytics/seals")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["seal_replacements_count"] is None
    assert data["summary"]["mtbsr_days"] is None
    assert len(data["leaks_by_pump_type"]) > 0


def test_get_material_analytics():
    fake = FakeLTSAAnalyticsService()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_ltsa_analytics_service] = lambda: fake

    response = client.get("/api/ltsa/analytics/materials")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["has_data"] is False
    assert data["summary"]["total_items_consumed"] is None


def test_get_maintenance_effectiveness():
    fake = FakeLTSAAnalyticsService()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_ltsa_analytics_service] = lambda: fake

    response = client.get("/api/ltsa/analytics/effectiveness")
    assert response.status_code == 200
    metrics = response.json()["data"]["metrics"]
    assert metrics["pm_executed"] == 53
    assert metrics["confirmed_leaks"] == 52
    assert metrics["proactive_ratio_percent"] == 50.5
    assert metrics["first_time_fix_rate"] is None

