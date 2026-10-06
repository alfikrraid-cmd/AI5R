"""Comprehensive RBAC and data scoping test suite for PERTAMINA_ENGINEER with ALL area scope.

Proves:
1. Pure logic: resolve_area_scope returns AREA_CODES (all 6 physical areas)
   when data_scope_type is 'ALL'.
2. Role separation: PERTAMINA_ENGINEER is never an unrestricted super role;
   resolve_area_scope returns AREA_CODES, never None.
3. Fail-closed: NULL or unrecognized scope returns frozenset() (zero access).
4. API enforcement: In-scope pumps across all 6 areas are readable;
   open work orders, last PM, and last CM sub-resources are accessible.
5. Least privilege: Admin routes (create user, status, password reset) and
   write routes (record edits, installation links) remain strictly 403 Forbidden.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_cm_report_gateway,
    get_current_user,
    get_maintenance_history_gateway,
    get_pm_occurrence_gateway,
    get_pump_gateway,
    get_work_order_gateway,
)
from API.auth_service import (  # noqa: E402
    _UNRESTRICTED_ROLES,
    ROLE_PERMISSIONS,
    AuthenticatedIdentity,
    resolve_area_scope,
)
from API.pump_area_scope import AREA_CODES, is_area_in_scope  # noqa: E402

client = TestClient(app)

_TEST_PUMPS = [
    {"tag_number": "110-P-9A", "area": "HOC", "name": "Crude Charge Pump A"},
    {"tag_number": "200-P-1A", "area": "HSC", "name": "Sour Water Pump A"},
    {"tag_number": "300-P-1A", "area": "S_PAKNING", "name": "Pakning Transfer Pump A"},
    {"tag_number": "400-P-1A", "area": "HCC", "name": "Heavy Coker Pump A"},
    {"tag_number": "500-P-1A", "area": "OM", "name": "Oil Movement Pump A"},
    {"tag_number": "600-P-1A", "area": "UTL", "name": "Utility Boiler Feed Pump A"},
]


class MockPumpGateway:
    def list_pumps(self):
        return {"success": True, "message": "ok", "count": len(_TEST_PUMPS), "data": list(_TEST_PUMPS)}

    def get_pump(self, tag_number):
        match = next((p for p in _TEST_PUMPS if p["tag_number"] == tag_number), None)
        if match is None:
            return {"success": False, "message": "not found", "data": None}
        return {"success": True, "message": "ok", "data": dict(match)}


class MockWorkOrderGateway:
    def list_work_orders(self):
        return {
            "success": True,
            "data": [
                {"work_order_number": "WO-001", "asset_code": "110-P-9A", "closed_at": None},
                {"work_order_number": "WO-002", "asset_code": "200-P-1A", "closed_at": None},
                {"work_order_number": "WO-003", "asset_code": "300-P-1A", "closed_at": None},
                {"work_order_number": "WO-004", "asset_code": "400-P-1A", "closed_at": None},
                {"work_order_number": "WO-005", "asset_code": "500-P-1A", "closed_at": None},
                {"work_order_number": "WO-006", "asset_code": "600-P-1A", "closed_at": None},
            ],
        }


def _make_identity(role: str = "PERTAMINA_ENGINEER", *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="user-pertamina-1",
        email="engineer@pertamina.test",
        username="pertamina.engineer",
        name="Pertamina Maintenance Engineer",
        organization_id="org-pertamina-ru2",
        organization_code="PERTAMINA_RU_II",
        role=role,
        permissions=ROLE_PERMISSIONS.get(role, frozenset()),
        data_scope_type=data_scope_type,
        data_scope_value=data_scope_value,
    )


@pytest.fixture(autouse=True)
def setup_overrides():
    app.dependency_overrides[get_pump_gateway] = lambda: MockPumpGateway()
    app.dependency_overrides[get_work_order_gateway] = lambda: MockWorkOrderGateway()

    mock_maint = MagicMock()
    mock_maint.list_maintenance_records.return_value = {"success": True, "data": []}
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: mock_maint

    mock_pm = MagicMock()
    mock_pm.list_pm_occurrences.return_value = {"success": True, "data": []}
    app.dependency_overrides[get_pm_occurrence_gateway] = lambda: mock_pm

    mock_cm = MagicMock()
    mock_cm.list_cm_reports.return_value = {"success": True, "data": []}
    app.dependency_overrides[get_cm_report_gateway] = lambda: mock_cm

    yield

    app.dependency_overrides.pop(get_pump_gateway, None)
    app.dependency_overrides.pop(get_work_order_gateway, None)
    app.dependency_overrides.pop(get_maintenance_history_gateway, None)
    app.dependency_overrides.pop(get_pm_occurrence_gateway, None)
    app.dependency_overrides.pop(get_cm_report_gateway, None)
    app.dependency_overrides.pop(get_current_user, None)


class TestPertaminaEngineerResolveAreaScope:
    def test_pertamina_engineer_not_in_unrestricted_roles(self):
        assert "PERTAMINA_ENGINEER" not in _UNRESTRICTED_ROLES
        assert "PERTAMINA_VIEWER" not in _UNRESTRICTED_ROLES

    def test_all_scope_returns_exact_area_codes(self):
        ident = _make_identity("PERTAMINA_ENGINEER", data_scope_type="ALL")
        scope = resolve_area_scope(ident)
        assert scope == AREA_CODES
        assert scope == frozenset({"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"})

    def test_all_scope_case_insensitive(self):
        ident = _make_identity("PERTAMINA_ENGINEER", data_scope_type="all")
        assert resolve_area_scope(ident) == AREA_CODES

    def test_all_scope_with_whitespace(self):
        ident = _make_identity("PERTAMINA_ENGINEER", data_scope_type="  ALL  ")
        assert resolve_area_scope(ident) == AREA_CODES

    def test_all_scope_ignores_data_scope_value(self):
        ident = _make_identity("PERTAMINA_ENGINEER", data_scope_type="ALL", data_scope_value="DUMMY")
        assert resolve_area_scope(ident) == AREA_CODES

    def test_pertamina_viewer_with_all_scope(self):
        ident = _make_identity("PERTAMINA_VIEWER", data_scope_type="ALL")
        assert resolve_area_scope(ident) == AREA_CODES

    def test_negative_all_scope_is_never_none_unrestricted(self):
        # Even with ALL scope, the resolved scope must NOT be None.
        # None grants superuser bypass across arbitrary values.
        # AREA_CODES explicitly bounds visibility to valid LTSA physical areas.
        ident = _make_identity("PERTAMINA_ENGINEER", data_scope_type="ALL")
        scope = resolve_area_scope(ident)
        assert scope is not None
        assert isinstance(scope, frozenset)
        assert scope == AREA_CODES
        assert is_area_in_scope("NON_LTSA_AREA", scope) is False
        assert is_area_in_scope(None, scope) is False

    def test_null_scope_fails_closed(self):
        ident = _make_identity("PERTAMINA_ENGINEER", data_scope_type=None)
        assert resolve_area_scope(ident) == frozenset()

    def test_unrecognized_scope_type_fails_closed(self):
        ident = _make_identity("PERTAMINA_ENGINEER", data_scope_type="ZONE", data_scope_value="ZONE_1")
        assert resolve_area_scope(ident) == frozenset()


class TestPertaminaEngineerApiRoutesWithAllScope:
    def test_list_pumps_sees_all_six_areas(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        res = client.get("/api/ltsa/pumps")
        assert res.status_code == 200
        body = res.json()
        assert body["count"] == 6
        areas = {p["area"] for p in body["data"]}
        assert areas == {"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"}

    def test_get_individual_pump_details_across_all_six_areas(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        for pump in _TEST_PUMPS:
            tag = pump["tag_number"]
            res = client.get(f"/api/ltsa/pumps/{tag}")
            assert res.status_code == 200
            assert res.json()["data"]["tag_number"] == tag
            assert res.json()["data"]["area"] == pump["area"]

    def test_get_nonexistent_pump_returns_404(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        res = client.get("/api/ltsa/pumps/999-P-99")
        assert res.status_code == 404

    def test_subresources_accessible_for_all_six_areas(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        for pump in _TEST_PUMPS:
            tag = pump["tag_number"]
            res_wo = client.get(f"/api/ltsa/pumps/{tag}/workorders")
            assert res_wo.status_code == 200

            res_pm = client.get(f"/api/ltsa/pumps/{tag}/last-pm")
            assert res_pm.status_code == 200

            res_cm = client.get(f"/api/ltsa/pumps/{tag}/last-cm")
            assert res_cm.status_code == 200


class TestPertaminaEngineerFailClosedOnNullScope:
    def test_list_pumps_returns_empty_when_scope_is_null(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type=None
        )
        res = client.get("/api/ltsa/pumps")
        assert res.status_code == 200
        body = res.json()
        assert body["count"] == 0
        assert body["data"] == []

    def test_get_pump_detail_returns_404_when_scope_is_null(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type=None
        )
        for pump in _TEST_PUMPS:
            res = client.get(f"/api/ltsa/pumps/{pump['tag_number']}")
            assert res.status_code == 404


class TestPertaminaEngineerPermissionsGuards:
    """Verifies that an ALL-scoped Pertamina Engineer has zero admin or write permissions."""

    def test_cannot_list_admin_users(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        res = client.get("/api/admin/users")
        assert res.status_code == 403

    def test_cannot_create_admin_user(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        res = client.post(
            "/api/admin/users",
            json={
                "username": "new_user",
                "password": "Password123!",
                "organization_id": "org-pertamina-ru2",
                "role": "PERTAMINA_VIEWER",
            },
        )
        assert res.status_code == 403

    def test_cannot_change_user_status(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        res = client.patch(
            "/api/admin/users/user-123/status",
            json={"status": "INACTIVE"},
        )
        assert res.status_code == 403

    def test_cannot_reset_user_password(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        res = client.post(
            "/api/admin/users/user-123/password-reset",
            json={"new_password": "NewSecretPassword123!"},
        )
        assert res.status_code == 403

    def test_cannot_edit_records(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        res = client.post(
            "/api/ltsa/records/edit",
            json={
                "entity_type": "PUMP",
                "entity_id": "110-P-9A",
                "field_name": "name",
                "new_value": "Modified Name",
                "reason": "Unauthorized Edit Attempt",
            },
        )
        assert res.status_code == 403

    def test_cannot_link_installation_report(self):
        app.dependency_overrides[get_current_user] = lambda: _make_identity(
            "PERTAMINA_ENGINEER", data_scope_type="ALL"
        )
        res = client.post(
            "/api/ltsa/installation-reports/INST-001/link-installation",
            json={
                "seal_unit_id": "SEAL-1",
                "installation_event_id": "EVT-1",
                "pump_tag_number": "110-P-9A",
                "reason": "Unauthorized Link Attempt",
            },
        )
        assert res.status_code == 403
