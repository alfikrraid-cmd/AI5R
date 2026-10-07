"""LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- Executive Dashboard
authorization (dashboard.read AND pump.read) and the area filter
(resolve_area_scope narrowed by ?area=; 403 area_not_in_scope, 422
invalid_area), across all eight dashboard routes.

The fleet fixture below reproduces the frozen production census
distribution of ltsa_pumps.area (252 pumps, 22 raw values) as acceptance
evidence only -- application code hard-codes none of these counts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_basic_fleet_overview_service,
    get_current_user,
    get_fleet_executive_summary_service,
    get_fleet_reliability_service,
    get_ltsa_analytics_service,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity, resolve_area_scope  # noqa: E402
from API.basic_fleet_overview_service import BasicFleetOverviewService  # noqa: E402
from API.pump_area_scope import (  # noqa: E402
    AreaNotInScopeError,
    InvalidAreaError,
    authorized_area_options,
    resolve_requested_scope,
)

client = TestClient(app)

PERTAMINA_ALL = frozenset({"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"})

# Frozen production census (R6A1): raw ltsa_pumps.area -> pump count.
PRODUCTION_AREA_CENSUS = {
    "HCC": 82, "HOC": 54, "HSC": 37, "OM": 30, "OIL MOVEMENT": 1, "UTL": 15, "UTILITIES": 1,
    "S_PAKNING": 3, "SPK": 7,
    "FRAKSINASI": 3, "Fraksinasi": 2, "REAKTOR": 4, "Reaktor": 3, "DCU": 2, "AMINE": 1, "CDU": 1,
    "DHDT": 1, "H2 PLAN": 1, "ITY": 1, "PL1": 1, "PL2": 1, "VACUUM": 1,
}
EXPECTED_PERTAMINA_COUNTS = {"HOC": 54, "HSC": 37, "S_PAKNING": 10, "HCC": 82, "OM": 31, "UTL": 16}

DASHBOARD_ROUTES = (
    "/api/ltsa/fleet/overview",
    "/api/ltsa/fleet/reliability",
    "/api/ltsa/fleet/powerbi",
    "/api/ltsa/analytics/executive",
    "/api/ltsa/analytics/seals",
    "/api/ltsa/analytics/materials",
    "/api/ltsa/analytics/effectiveness",
)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="u1", email="u1@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


def _pertamina(scope_type=None, scope_value=None):
    return _identity("PERTAMINA_ENGINEER", data_scope_type=scope_type, data_scope_value=scope_value)


class _ScopeRecorder:
    """Stands in for every dashboard service; records the scope each route
    actually passed and returns a minimal payload."""

    def __init__(self):
        self.scopes = []
        self.material_kwargs = None

    def build(self, *, scope=None):
        self.scopes.append(scope)
        return _Snapshot()

    def get_filter_options(self, *, scope=None):
        self.scopes.append(scope)
        return {"areas": [], "pumps": [], "date_range": {}}

    def get_executive_analytics(self, **kwargs):
        self.scopes.append(kwargs["scope"])
        return {"kpis": {}}

    def get_seal_analytics(self, **kwargs):
        self.scopes.append(kwargs["scope"])
        return {"summary": {}}

    def get_material_analytics(self, **kwargs):
        self.scopes.append(kwargs["scope"])
        self.material_kwargs = kwargs
        return {"has_data": False}

    def get_maintenance_effectiveness(self, **kwargs):
        self.scopes.append(kwargs["scope"])
        return {"metrics": {}}


class _Snapshot:
    pass


@pytest.fixture
def recorder(monkeypatch):
    import routers.fleet as fleet_router

    recorder = _ScopeRecorder()
    # Fleet routes serialize a dataclass; the recorder returns a stand-in.
    monkeypatch.setattr(fleet_router.dataclasses, "asdict", lambda obj: {})
    monkeypatch.setattr(fleet_router, "build_fleet_insight", lambda summary: None)
    for dependency in (
        get_basic_fleet_overview_service,
        get_fleet_reliability_service,
        get_fleet_executive_summary_service,
        get_ltsa_analytics_service,
    ):
        app.dependency_overrides[dependency] = lambda: recorder
    yield recorder
    app.dependency_overrides.clear()


def _as(identity):
    app.dependency_overrides[get_current_user] = lambda: identity


# --- Role matrix ------------------------------------------------------------


@pytest.mark.parametrize(
    "role,expected",
    [
        ("SUPERUSER", True), ("TAP_ADMIN", True), ("TAP_ENGINEER", True),
        ("PERTAMINA_ENGINEER", True), ("PERTAMINA_VIEWER", False), ("JOHN_CRANE_ENGINEER", False),
    ],
)
def test_dashboard_read_role_matrix(role, expected):
    assert ("dashboard.read" in ROLE_PERMISSIONS[role]) is expected


def test_pertamina_engineer_gains_no_internal_admin_write_or_master_permission():
    perms = ROLE_PERMISSIONS["PERTAMINA_ENGINEER"]
    for forbidden in (
        "internal_inventory.read", "internal_component.read", "admin.users", "admin.superuser",
        "master.edit", "record.edit", "maintenance.write", "maintenance.admin_review",
        "maintenance.technical_review", "import.execute", "installation.write", "seal.lifecycle_write",
        "audit.read_full",
    ):
        assert forbidden not in perms
    assert perms == frozenset(
        {"pump.read", "seal.read", "inventory.read", "maintenance.read", "condition.read",
         "drawing.read", "engineering_ai.ask", "dashboard.read"}
    )


@pytest.mark.parametrize("role", ["PERTAMINA_VIEWER", "JOHN_CRANE_ENGINEER"])
@pytest.mark.parametrize("path", DASHBOARD_ROUTES + ("/api/ltsa/analytics/filters",))
def test_roles_without_dashboard_read_are_rejected_on_every_route(recorder, role, path):
    _as(_identity(role, data_scope_type="ALL"))
    response = client.get(path)
    assert response.status_code == 403
    assert response.json()["detail"] == "Missing permission: dashboard.read"
    assert recorder.scopes == []


# --- resolve_requested_scope ------------------------------------------------


def test_resolve_requested_scope_semantics():
    assert resolve_requested_scope(PERTAMINA_ALL, None) == PERTAMINA_ALL
    assert resolve_requested_scope(PERTAMINA_ALL, "ALL") == PERTAMINA_ALL
    assert resolve_requested_scope(PERTAMINA_ALL, "all") == PERTAMINA_ALL
    assert resolve_requested_scope(None, None) is None  # TAP/SUPERUSER: unchanged, unrestricted
    assert resolve_requested_scope(None, "HOC") == frozenset({"HOC"})
    assert resolve_requested_scope(PERTAMINA_ALL, "S. Pakning") == frozenset({"S_PAKNING"})
    assert resolve_requested_scope(PERTAMINA_ALL, "spk") == frozenset({"S_PAKNING"})
    assert resolve_requested_scope(frozenset(), None) == frozenset()  # NULL scope stays fail-closed
    with pytest.raises(AreaNotInScopeError):
        resolve_requested_scope(frozenset({"HOC"}), "HSC")
    with pytest.raises(AreaNotInScopeError):
        resolve_requested_scope(frozenset(), "HOC")
    for unknown in ("REAKTOR", "NOWHERE", "HOC;DROP"):
        with pytest.raises(InvalidAreaError):
            resolve_requested_scope(PERTAMINA_ALL, unknown)
        with pytest.raises(InvalidAreaError):
            resolve_requested_scope(None, unknown)


def test_authorized_area_options():
    six = [o["code"] for o in authorized_area_options(PERTAMINA_ALL)]
    assert six == ["HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"]
    assert [o["code"] for o in authorized_area_options(None)] == six
    assert authorized_area_options(frozenset({"HOC"})) == [{"code": "HOC", "label": "HOC"}]
    assert [o["code"] for o in authorized_area_options(resolve_area_scope(_pertamina("MA", "MA2")))] == [
        "HSC", "S_PAKNING", "HCC",
    ]
    assert authorized_area_options(frozenset()) == []
    assert {"code": "S_PAKNING", "label": "S. Pakning"} in authorized_area_options(PERTAMINA_ALL)


# --- Route-level area filter ------------------------------------------------


@pytest.mark.parametrize("area", [None, "ALL", "HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"])
def test_pertamina_all_accepts_all_and_each_canonical_area_on_every_route(recorder, area):
    _as(_pertamina("ALL"))
    expected = PERTAMINA_ALL if area in (None, "ALL") else frozenset({area})
    for path in DASHBOARD_ROUTES:
        response = client.get(path, params={"area": area} if area else None)
        assert response.status_code == 200, path
    assert recorder.scopes == [expected] * len(DASHBOARD_ROUTES)


def test_area_hoc_user_gets_hoc_and_is_refused_hsc_on_every_route(recorder):
    _as(_pertamina("AREA", "HOC"))
    for path in DASHBOARD_ROUTES:
        assert client.get(path, params={"area": "HOC"}).status_code == 200
        refused = client.get(path, params={"area": "HSC"})
        assert refused.status_code == 403, path
        assert refused.json()["detail"] == "area_not_in_scope"
    # Only the HOC requests ever reached a service, each with exactly {HOC}.
    assert recorder.scopes == [frozenset({"HOC"})] * len(DASHBOARD_ROUTES)


def test_ma2_user_gets_its_three_areas_and_is_refused_hoc(recorder):
    _as(_pertamina("MA", "MA2"))
    for area in ("HSC", "S_PAKNING", "HCC"):
        assert client.get("/api/ltsa/fleet/overview", params={"area": area}).status_code == 200
    assert client.get("/api/ltsa/fleet/overview", params={"area": "HOC"}).status_code == 403
    assert client.get("/api/ltsa/fleet/overview").status_code == 200
    assert recorder.scopes[-1] == frozenset({"HSC", "S_PAKNING", "HCC"})


def test_null_scope_pertamina_all_is_fail_closed_and_specific_area_is_403(recorder):
    _as(_pertamina())
    assert client.get("/api/ltsa/analytics/executive").status_code == 200
    assert recorder.scopes == [frozenset()]
    assert client.get("/api/ltsa/analytics/executive", params={"area": "HOC"}).status_code == 403


def test_unknown_area_token_is_422_for_every_role(recorder):
    for identity in (_pertamina("ALL"), _identity("TAP_ADMIN")):
        _as(identity)
        for token in ("REAKTOR", "atlantis"):
            response = client.get("/api/ltsa/analytics/seals", params={"area": token})
            assert response.status_code == 422
            assert response.json()["detail"] == "invalid_area"
    assert recorder.scopes == []


def test_tap_and_superuser_keep_unrestricted_all_and_can_narrow(recorder):
    for role in ("SUPERUSER", "TAP_ADMIN", "TAP_ENGINEER"):
        _as(_identity(role))
        assert client.get("/api/ltsa/fleet/overview").status_code == 200
        assert client.get("/api/ltsa/fleet/overview", params={"area": "OM"}).status_code == 200
    assert recorder.scopes == [None, frozenset({"OM"})] * 3


def test_filters_route_returns_authorized_areas_from_full_scope_ignoring_area(recorder):
    _as(_pertamina("AREA", "HOC"))
    body = client.get("/api/ltsa/analytics/filters", params={"area": "HSC"}).json()
    assert body["data"]["authorized_areas"] == [{"code": "HOC", "label": "HOC"}]
    _as(_pertamina("ALL"))
    codes = [a["code"] for a in client.get("/api/ltsa/analytics/filters").json()["data"]["authorized_areas"]]
    assert codes == ["HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"]


def test_materials_route_passes_internal_component_permission_not_pump_read(recorder):
    _as(_pertamina("ALL"))
    client.get("/api/ltsa/analytics/materials")
    assert recorder.material_kwargs["include_internal_components"] is False
    _as(_identity("TAP_ENGINEER"))
    client.get("/api/ltsa/analytics/materials")
    assert recorder.material_kwargs["include_internal_components"] is True


# --- Real service over the production census distribution -------------------


class _CensusPumpGateway:
    def __init__(self):
        self._pumps = [
            {"tag_number": f"{raw}-{i}", "area": raw, "status": "RUNNING"}
            for raw, count in PRODUCTION_AREA_CENSUS.items()
            for i in range(count)
        ]

    def list_pumps(self):
        return {"data": list(self._pumps)}


class _Empty:
    def __getattr__(self, name):
        return lambda: {"data": []}


def _census_overview_service():
    return BasicFleetOverviewService(
        pump_gateway=_CensusPumpGateway(), work_order_gateway=_Empty(), pm_schedule_gateway=_Empty(),
        cm_report_gateway=_Empty(), seal_stock_gateway=_Empty(),
    )


def _pump_count(identity, area=None):
    app.dependency_overrides[get_basic_fleet_overview_service] = _census_overview_service
    _as(identity)
    try:
        response = client.get("/api/ltsa/fleet/overview", params={"area": area} if area else None)
        assert response.status_code == 200
        return response.json()["data"]
    finally:
        app.dependency_overrides.clear()


def test_census_fixture_matches_frozen_production_totals():
    assert sum(PRODUCTION_AREA_CENSUS.values()) == 252
    assert len(PRODUCTION_AREA_CENSUS) == 22


def test_pertamina_all_counts_finite_six_including_aliases_and_excludes_other_areas():
    data = _pump_count(_pertamina("ALL"))
    assert data["pump_count"] == 230
    for outside in ("FRAKSINASI", "Fraksinasi", "REAKTOR", "Reaktor", "DCU", "AMINE", "CDU", "DHDT",
                    "H2 PLAN", "ITY", "PL1", "PL2", "VACUUM"):
        assert outside not in data["area_distribution"]
    # Fleet-wide seal stock is withheld from a scoped overview.
    assert data["seal_stock_count"] is None


@pytest.mark.parametrize("area,expected", sorted(EXPECTED_PERTAMINA_COUNTS.items()))
def test_pertamina_all_each_area_count_matches_census_with_aliases(area, expected):
    assert _pump_count(_pertamina("ALL"), area)["pump_count"] == expected


def test_alias_coded_pumps_land_in_their_canonical_area():
    assert _pump_count(_pertamina("ALL"), "S_PAKNING")["area_distribution"] == {"S_PAKNING": 3, "SPK": 7}
    assert _pump_count(_pertamina("ALL"), "OM")["area_distribution"] == {"OM": 30, "OIL MOVEMENT": 1}
    assert _pump_count(_pertamina("ALL"), "UTL")["area_distribution"] == {"UTL": 15, "UTILITIES": 1}


def test_unrestricted_all_still_sees_the_whole_production_fleet():
    data = _pump_count(_identity("TAP_ADMIN"))
    assert data["pump_count"] == 252
    assert data["seal_stock_count"] == 0  # unrestricted + unfiltered keeps the fleet-wide figure
