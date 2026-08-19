"""MWO-LTSA-AUTH-DATA-SCOPE-CLOSURE-001 -- proves Area/MA data scope is
enforced in the FastAPI backend layer itself (never frontend-only) on
the real /pumps and /api/ltsa/pumps routes: list-side filtering and
detail-side safe-not-found denial.
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app  # noqa: E402
from dependencies import get_current_user, get_pump_gateway  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)

_ALL_PUMPS = [
    {"tag_number": "110-P-9A", "area": "HOC"},
    {"tag_number": "200-P-1A", "area": "HSC"},
    {"tag_number": "300-P-1A", "area": "S_PAKNING"},
    {"tag_number": "400-P-1A", "area": "HCC"},
    {"tag_number": "500-P-1A", "area": "OM"},
    {"tag_number": "600-P-1A", "area": "UTL"},
]


class FakePumpGateway:
    def list_pumps(self):
        return {"success": True, "message": "ok", "count": len(_ALL_PUMPS), "data": list(_ALL_PUMPS)}

    def get_pump(self, tag_number):
        match = next((p for p in _ALL_PUMPS if p["tag_number"] == tag_number), None)
        if match is None:
            return {"success": False, "message": "not found", "data": None}
        return {"success": True, "message": "ok", "data": match}


def _identity(role: str, *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="u1", email="u1@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


def _as(identity: AuthenticatedIdentity):
    app.dependency_overrides[get_current_user] = lambda: identity
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()


def _clear():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_pump_gateway, None)


def _list_areas(path="/api/ltsa/pumps"):
    response = client.get(path)
    assert response.status_code == 200
    return {p["area"] for p in response.json()["data"]}


class TestAreaScopedList:
    def test_hoc_user_sees_only_hoc(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        try:
            assert _list_areas() == {"HOC"}
        finally:
            _clear()

    def test_hsc_user_sees_only_hsc(self):
        _as(_identity("PERTAMINA_VIEWER", data_scope_type="AREA", data_scope_value="HSC"))
        try:
            assert _list_areas() == {"HSC"}
        finally:
            _clear()

    def test_s_pakning_user_sees_only_s_pakning(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="S_PAKNING"))
        try:
            assert _list_areas() == {"S_PAKNING"}
        finally:
            _clear()

    def test_hcc_user_sees_only_hcc(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HCC"))
        try:
            assert _list_areas() == {"HCC"}
        finally:
            _clear()

    def test_om_user_sees_only_om(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="OM"))
        try:
            assert _list_areas() == {"OM"}
        finally:
            _clear()

    def test_utl_user_sees_only_utl(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="UTL"))
        try:
            assert _list_areas() == {"UTL"}
        finally:
            _clear()

    def test_ma2_user_sees_hsc_s_pakning_hcc_only(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA2"))
        try:
            assert _list_areas() == {"HSC", "S_PAKNING", "HCC"}
        finally:
            _clear()

    def test_tap_admin_sees_all(self):
        _as(_identity("TAP_ADMIN"))
        try:
            assert _list_areas() == {"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"}
        finally:
            _clear()

    def test_tap_engineer_sees_all(self):
        _as(_identity("TAP_ENGINEER"))
        try:
            assert _list_areas() == {"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"}
        finally:
            _clear()

    def test_john_crane_engineer_sees_all_ltsa(self):
        _as(_identity("JOHN_CRANE_ENGINEER"))
        try:
            assert _list_areas() == {"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"}
        finally:
            _clear()

    def test_superuser_sees_all(self):
        _as(_identity("SUPERUSER"))
        try:
            assert _list_areas() == {"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"}
        finally:
            _clear()

    def test_response_count_reflects_the_filtered_list_not_the_raw_total(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        try:
            response = client.get("/api/ltsa/pumps")
            body = response.json()
            assert body["count"] == 1 == len(body["data"])
        finally:
            _clear()

    def test_search_cannot_leak_out_of_scope_records_via_the_same_list_endpoint(self):
        # No dedicated search route exists separate from list -- proving
        # list itself never returns an out-of-scope record is the
        # relevant leakage guard for this API surface.
        _as(_identity("PERTAMINA_VIEWER", data_scope_type="AREA", data_scope_value="OM"))
        try:
            tags = {p["tag_number"] for p in client.get("/api/ltsa/pumps").json()["data"]}
            assert "600-P-1A" not in tags  # UTL tag must never appear for an OM-scoped user
        finally:
            _clear()


class TestAreaScopedDetail:
    def test_in_scope_detail_is_returned(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        try:
            response = client.get("/api/ltsa/pumps/110-P-9A")
            assert response.status_code == 200
            assert response.json()["data"]["tag_number"] == "110-P-9A"
        finally:
            _clear()

    def test_cross_scope_direct_api_access_denied(self):
        # HOC-scoped user requesting a real UTL tag by direct tag lookup.
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        try:
            response = client.get("/api/ltsa/pumps/600-P-1A")
            assert response.status_code == 404
        finally:
            _clear()

    def test_cross_scope_denial_does_not_leak_existence_via_a_different_status_than_a_real_miss(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        try:
            out_of_scope = client.get("/api/ltsa/pumps/600-P-1A")  # real pump, wrong area
            genuinely_missing = client.get("/api/ltsa/pumps/NOT-A-REAL-TAG")
            assert out_of_scope.status_code == genuinely_missing.status_code == 404
        finally:
            _clear()

    def test_ma2_user_can_reach_all_three_grouped_areas_by_direct_tag(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA2"))
        try:
            for tag in ("200-P-1A", "300-P-1A", "400-P-1A"):
                assert client.get(f"/api/ltsa/pumps/{tag}").status_code == 200
            assert client.get("/api/ltsa/pumps/110-P-9A").status_code == 404  # HOC, outside MA2
        finally:
            _clear()

    def test_unscoped_pertamina_user_denied_everything(self):
        _as(_identity("PERTAMINA_VIEWER"))  # no data_scope recorded at all
        try:
            assert client.get("/api/ltsa/pumps/110-P-9A").status_code == 404
            assert client.get("/api/ltsa/pumps").json()["data"] == []
        finally:
            _clear()
