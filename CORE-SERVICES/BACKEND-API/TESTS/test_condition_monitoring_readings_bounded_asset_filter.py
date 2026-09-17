"""MWO-R2C3 -- GET /api/ltsa/condition-monitoring-readings?asset_code=...

Bounded, exact-match single-asset read path for Mechanical Seal Detail's
"Related Condition Monitoring" group. Reuses the repository's existing
list_by_asset(asset_code) (already trusted by copilot_ask_service.py/
equipment_360_service.py/ltsa_knowledge_service.py) -- no new SQL, no
new repository, no new table. Omitting asset_code must preserve the
pre-existing list_all()/limit/offset contract byte-for-byte.

Fake repository only defines list_all/list_by_asset -- any call to a
Corrective Maintenance method (e.g. list_cm_reports) would raise
AttributeError, so "no Corrective Maintenance API is involved" is
proven by construction, not just by inspection.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_condition_monitoring_reading_repository,
    get_current_user,
    get_pump_gateway,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)

_PUMP_AREAS = {"211-P-8A": "HOC", "211-P-9A": "HSC"}


class FakePumpGateway:
    def get_pump(self, tag_number):
        area = _PUMP_AREAS.get(tag_number)
        if area is None:
            return {"success": False, "data": None}
        return {"success": True, "data": {"tag_number": tag_number, "area": area}}

    def list_pumps(self):
        return {"success": True, "count": len(_PUMP_AREAS), "data": [{"tag_number": t, "area": a} for t, a in _PUMP_AREAS.items()]}


class FakeConditionMonitoringReadingRepository:
    """Only list_all/list_by_asset exist -- no Corrective Maintenance
    method is even definable to call by accident."""

    def __init__(self):
        self.calls: list[tuple] = []
        self._by_asset = {
            "211-P-8A": [
                {"condition_monitoring_reading_code": "CMONR-1", "asset_code": "211-P-8A", "reading_date": "2026-06-01", "mechanical_seal_leak_de": False, "mechanical_seal_leak_nde": True, "mechseal_temp_de": 61.5, "mechseal_temp_nde": 58.2, "workflow_status": "REVIEWED", "finding": "Minor NDE weep"},
                {"condition_monitoring_reading_code": "CMONR-2", "asset_code": "211-P-8A", "reading_date": "2026-05-01", "mechanical_seal_leak_de": False, "mechanical_seal_leak_nde": False, "mechseal_temp_de": 55.0, "mechseal_temp_nde": 54.1, "workflow_status": "REVIEWED", "finding": None},
            ],
            "211-P-9A": [
                {"condition_monitoring_reading_code": "CMONR-9", "asset_code": "211-P-9A", "reading_date": "2026-06-02", "mechanical_seal_leak_de": True, "mechanical_seal_leak_nde": False, "mechseal_temp_de": 70.0, "mechseal_temp_nde": 69.0, "workflow_status": "SUBMITTED", "finding": "DE leak observed"},
            ],
            "211-P-NO-READINGS": [],
        }

    def list_all(self, *, scope=None, limit=25, offset=0):
        self.calls.append(("list_all", scope, limit, offset))
        return {"success": True, "message": "ok", "count": 0, "data": [], "items": [], "total": 0, "limit": limit, "offset": offset}

    def list_by_asset(self, asset_code):
        self.calls.append(("list_by_asset", asset_code))
        return list(self._by_asset.get(asset_code, []))


def _identity(role: str = "SUPERUSER", *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="actor-1", email="actor-1@tap.internal", organization_id="org-tap",
        organization_code="TAP", role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


@pytest.fixture(autouse=True)
def _clear_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _identity()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    yield
    app.dependency_overrides.clear()


def _fake():
    fake = FakeConditionMonitoringReadingRepository()
    app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: fake
    return fake


def test_without_asset_code_preserves_existing_list_all_behavior():
    fake = _fake()

    response = client.get("/api/ltsa/condition-monitoring-readings?limit=10&offset=5")

    assert response.status_code == 200
    assert fake.calls == [("list_all", None, 10, 5)]


def test_with_asset_code_calls_list_by_asset_exactly():
    fake = _fake()

    response = client.get("/api/ltsa/condition-monitoring-readings?asset_code=211-P-8A")

    assert response.status_code == 200
    assert fake.calls == [("list_by_asset", "211-P-8A")]
    body = response.json()
    assert body["success"] is True
    assert [r["condition_monitoring_reading_code"] for r in body["data"]] == ["CMONR-1", "CMONR-2"]


def test_different_asset_code_never_returns_another_assets_rows():
    fake = _fake()

    response_8a = client.get("/api/ltsa/condition-monitoring-readings?asset_code=211-P-8A")
    response_9a = client.get("/api/ltsa/condition-monitoring-readings?asset_code=211-P-9A")

    codes_8a = {r["condition_monitoring_reading_code"] for r in response_8a.json()["data"]}
    codes_9a = {r["condition_monitoring_reading_code"] for r in response_9a.json()["data"]}
    assert codes_8a == {"CMONR-1", "CMONR-2"}
    assert codes_9a == {"CMONR-9"}
    assert codes_8a.isdisjoint(codes_9a)


def test_empty_result_for_asset_with_no_readings_is_a_normal_200():
    fake = _fake()

    response = client.get("/api/ltsa/condition-monitoring-readings?asset_code=211-P-NO-READINGS")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["count"] == 0
    assert body["total"] == 0


def test_out_of_scope_asset_returns_empty_not_another_areas_data():
    fake = _fake()
    app.dependency_overrides[get_current_user] = lambda: _identity(
        "PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HSC"
    )

    response = client.get("/api/ltsa/condition-monitoring-readings?asset_code=211-P-8A")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_in_scope_asset_still_returns_real_rows():
    fake = _fake()
    app.dependency_overrides[get_current_user] = lambda: _identity(
        "PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"
    )

    response = client.get("/api/ltsa/condition-monitoring-readings?asset_code=211-P-8A")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
