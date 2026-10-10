"""LTSA_PERTAMINA_RBAC_SCOPE_AND_REQUEST_R2 -- Pertamina scope matrix.

ROLE decides what a user may do, SCOPE decides which assets:
- ALL   -> every LTSA asset, including raw area labels outside the six
           AREA_CODES (REAKTOR, FRAKSINASI, H2 PLAN, DCU, ...); never the
           unrestricted None.
- AREA  -> one governed area (raw-area token mapping, unchanged by R2).
- MA    -> MA1 / MA2 / MA3_4 (MA3_4 = MA3 + MA4 = UTL + OM).
- NULL / unknown type / unknown value -> fail closed (no assets).
PERTAMINA_ENGINEER stays read-only: every maintenance/installation/master
write and every admin route is denied whatever the scope.
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
from dependencies import get_current_user, get_pump_gateway  # noqa: E402
from API.auth_service import (  # noqa: E402
    _UNRESTRICTED_ROLES,
    ROLE_PERMISSIONS,
    AuthenticatedIdentity,
    resolve_area_scope,
)
from API.pump_area_scope import (  # noqa: E402
    ALL_ASSETS_SCOPE,
    MA_SCOPE_GROUPS,
    is_all_assets_scope,
    scope_sql_condition,
)

client = TestClient(app)

# One pump per governed area (incl. the SPK / OIL MOVEMENT aliases) plus the
# raw area labels that the pre-R2 ALL scope silently hid.
_PUMPS = [
    {"tag_number": "101-P-HOC", "area": "HOC"},
    {"tag_number": "102-P-HSC", "area": "HSC"},
    {"tag_number": "103-P-SPK", "area": "SPK"},
    {"tag_number": "104-P-HCC", "area": "HCC"},
    {"tag_number": "105-P-OM", "area": "OIL MOVEMENT"},
    {"tag_number": "106-P-UTL", "area": "UTL"},
    {"tag_number": "211-P-1A", "area": "REAKTOR"},
    {"tag_number": "211-P-13AR", "area": "FRAKSINASI"},
    {"tag_number": "701-P-1A", "area": "H2 PLAN"},
    {"tag_number": "100-P-6B", "area": "DCU"},
]
_ALL_TAGS = {p["tag_number"] for p in _PUMPS}
_EXPECTED_BY_SCOPE = {
    ("AREA", "HOC"): {"101-P-HOC"},
    ("AREA", "HSC"): {"102-P-HSC"},
    ("AREA", "S_PAKNING"): {"103-P-SPK"},
    ("AREA", "HCC"): {"104-P-HCC"},
    ("AREA", "OM"): {"105-P-OM"},
    ("AREA", "UTL"): {"106-P-UTL"},
    ("MA", "MA1"): {"101-P-HOC"},
    ("MA", "MA2"): {"102-P-HSC", "103-P-SPK", "104-P-HCC"},
    ("MA", "MA3_4"): {"105-P-OM", "106-P-UTL"},
}


class _PumpGateway:
    def list_pumps(self):
        return {"success": True, "message": "ok", "count": len(_PUMPS), "data": [dict(p) for p in _PUMPS]}

    def get_pump(self, tag_number):
        match = next((p for p in _PUMPS if p["tag_number"] == tag_number), None)
        if match is None:
            return {"success": False, "message": "not found", "data": None}
        return {"success": True, "message": "ok", "data": dict(match)}


def _identity(role="PERTAMINA_ENGINEER", scope_type=None, scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="user-r2", email="r2@pertamina.test", username="r2", name="R2",
        organization_id="org-pertamina-ru2", organization_code="PERTAMINA_RU_II",
        role=role, permissions=ROLE_PERMISSIONS.get(role, frozenset()),
        data_scope_type=scope_type, data_scope_value=scope_value,
    )


@pytest.fixture(autouse=True)
def _overrides():
    app.dependency_overrides[get_pump_gateway] = lambda: _PumpGateway()
    yield
    app.dependency_overrides.pop(get_pump_gateway, None)
    app.dependency_overrides.pop(get_current_user, None)


def _as(identity):
    app.dependency_overrides[get_current_user] = lambda: identity


def _listed_tags(identity) -> set[str]:
    _as(identity)
    res = client.get("/api/ltsa/pumps")
    assert res.status_code == 200
    return {p["tag_number"] for p in res.json()["data"]}


# -- resolve_area_scope ------------------------------------------------------


def test_all_scope_is_the_governed_all_assets_scope_never_unrestricted():
    scope = resolve_area_scope(_identity(scope_type="ALL"))
    assert scope is not None
    assert scope is ALL_ASSETS_SCOPE
    assert is_all_assets_scope(scope)
    assert "PERTAMINA_ENGINEER" not in _UNRESTRICTED_ROLES


def test_ma3_4_is_exactly_ma3_plus_ma4():
    assert MA_SCOPE_GROUPS["MA3_4"] == frozenset({"UTL", "OM"})
    assert resolve_area_scope(_identity(scope_type="MA", scope_value="MA3_4")) == frozenset({"UTL", "OM"})


@pytest.mark.parametrize(
    ("scope_type", "scope_value"),
    [
        (None, None),
        ("", None),
        ("ZONE", "Z1"),
        ("AREA", None),
        ("AREA", "REAKTOR"),
        ("AREA", "hcc"),
        ("MA", None),
        ("MA", "MA5"),
        ("MA", "MA3&4"),
    ],
)
def test_null_or_invalid_scope_fails_closed(scope_type, scope_value):
    assert resolve_area_scope(_identity(scope_type=scope_type, scope_value=scope_value)) == frozenset()


# -- SQL counterpart ---------------------------------------------------------


def test_scope_sql_condition_for_each_scope_kind():
    quote = lambda v: f"'{v}'"  # noqa: E731
    assert scope_sql_condition(None, "pump.area", quote) is None
    assert scope_sql_condition(ALL_ASSETS_SCOPE, "pump.area", quote) == "pump.area IS NOT NULL"
    assert scope_sql_condition(frozenset(), "pump.area", quote) == "FALSE"
    assert scope_sql_condition(frozenset({"OM", "HCC"}), "pump.area", quote) == "pump.area IN ('HCC', 'OM')"


# -- API: list + detail ------------------------------------------------------


def test_all_scope_lists_every_ltsa_pump_including_other_area_labels():
    assert _listed_tags(_identity(scope_type="ALL")) == _ALL_TAGS


def test_all_scope_opens_detail_for_previously_hidden_pumps():
    _as(_identity(scope_type="ALL"))
    for tag in ("211-P-1A", "211-P-13AR", "701-P-1A", "100-P-6B"):
        assert client.get(f"/api/ltsa/pumps/{tag}").status_code == 200


@pytest.mark.parametrize(("scope", "expected"), sorted(_EXPECTED_BY_SCOPE.items()))
def test_area_and_ma_scopes_list_only_their_assets(scope, expected):
    assert _listed_tags(_identity(scope_type=scope[0], scope_value=scope[1])) == expected


@pytest.mark.parametrize(
    ("scope", "outside_tag"),
    [
        (("AREA", "HCC"), "105-P-OM"),
        (("AREA", "HCC"), "211-P-1A"),
        (("AREA", "HOC"), "104-P-HCC"),
        (("AREA", "OM"), "101-P-HOC"),
        (("AREA", "UTL"), "105-P-OM"),
        (("MA", "MA1"), "102-P-HSC"),
        (("MA", "MA2"), "101-P-HOC"),
        (("MA", "MA3_4"), "104-P-HCC"),
    ],
)
def test_direct_detail_request_outside_scope_is_denied(scope, outside_tag):
    _as(_identity(scope_type=scope[0], scope_value=scope[1]))
    assert client.get(f"/api/ltsa/pumps/{outside_tag}").status_code == 404


def test_null_scope_lists_nothing_and_denies_detail():
    assert _listed_tags(_identity(scope_type=None)) == set()
    _as(_identity(scope_type=None))
    assert client.get("/api/ltsa/pumps/104-P-HCC").status_code == 404


# -- PERTAMINA_ENGINEER stays read-only whatever the scope ---------------------


_WRITE_CALLS = [
    ("post", "/api/ltsa/workorders", {"work_order_code": "WO-X", "description": "x", "asset_code": "104-P-HCC"}),
    ("post", "/work-orders", {"work_order_code": "WO-X", "description": "x", "asset_code": "104-P-HCC"}),
    ("post", "/api/ltsa/pm-occurrences", {"pm_occurrence_code": "PMO-X", "asset_code": "104-P-HCC", "occurrence_date": "2026-10-01"}),
    ("patch", "/api/ltsa/pm-occurrences/PMO-X", {"remarks": "x"}),
    ("post", "/api/ltsa/pm-schedules", {"pm_schedule_code": "PMS-X", "asset_code": "104-P-HCC"}),
    ("post", "/api/ltsa/condition-monitoring-schedules", {"condition_monitoring_schedule_code": "CMS-X", "asset_code": "104-P-HCC"}),
    ("post", "/api/ltsa/records/edit", {"record_type": "pump", "record_id": "104-P-HCC", "changes": {}}),
    ("post", "/api/ltsa/installation-reports/INSTL-X/link-installation", {}),
    ("post", "/api/admin/users", {"username": "x", "password": "Passw0rd!x", "role": "PERTAMINA_ENGINEER", "organization_id": "o"}),
]


@pytest.mark.parametrize("scope_type", ["ALL", "AREA", "MA"])
@pytest.mark.parametrize(("method", "path", "body"), _WRITE_CALLS)
def test_pertamina_engineer_cannot_write_or_administer_in_any_scope(scope_type, method, path, body):
    value = {"ALL": None, "AREA": "HCC", "MA": "MA2"}[scope_type]
    _as(_identity(scope_type=scope_type, scope_value=value))
    res = getattr(client, method)(path, json=body)
    assert res.status_code == 403, (path, res.status_code, res.text[:200])


def test_pertamina_engineer_permissions_are_view_and_request_only():
    perms = ROLE_PERMISSIONS["PERTAMINA_ENGINEER"]
    assert perms == frozenset(
        {
            "pump.read", "seal.read", "inventory.read", "maintenance.read",
            "condition.read", "drawing.read", "engineering_ai.ask", "dashboard.read",
            "maintenance.request", "installation.request",
        }
    )
    assert not any(p.endswith((".write", ".edit", ".manage", ".upload", ".execute", ".users")) for p in perms)


# -- unrestricted roles unchanged ---------------------------------------------


@pytest.mark.parametrize("role", ["SUPERUSER", "TAP_ADMIN", "TAP_ENGINEER", "JOHN_CRANE_ENGINEER"])
def test_tap_and_john_crane_roles_stay_unrestricted_whatever_scope_is_recorded(role):
    assert resolve_area_scope(_identity(role=role)) is None
    assert resolve_area_scope(_identity(role=role, scope_type="AREA", scope_value="HOC")) is None
    assert _listed_tags(_identity(role=role)) == _ALL_TAGS
