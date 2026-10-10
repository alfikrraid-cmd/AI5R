"""LTSA_PERTAMINA_RBAC_SCOPE_AND_REQUEST_R2 -- PM / CM / Installation requests.

PERTAMINA_ENGINEER is VIEW + REQUEST only: it may submit a request for an
asset inside its scope (ALL / AREA / MA), never for one outside it, and the
request never touches a work order, PM/CM or installation record.
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
    get_asset_registry_repository,
    get_current_user,
    get_pump_gateway,
    get_work_request_repository,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)

_ASSETS = {
    "104-P-HCC": "HCC",
    "105-P-OM": "OM",
    "101-P-HOC": "HOC",
    "211-P-1A": "REAKTOR",
    "701-MM-51": "H2Plan",  # agitator: asset_registry only, not in ltsa_pumps
}
_PUMPS = {tag: area for tag, area in _ASSETS.items() if "-MM-" not in tag}


class _PumpGateway:
    def get_pump(self, tag_number):
        if tag_number not in _PUMPS:
            return {"success": False, "message": "not found", "data": None}
        return {"success": True, "data": {"tag_number": tag_number, "area": _PUMPS[tag_number]}}


class _AssetRegistry:
    def get_asset(self, asset_code):
        if asset_code not in _ASSETS:
            return None
        return {"asset_code": asset_code, "area": _ASSETS[asset_code]}


class _WorkRequestRepository:
    def __init__(self):
        self.created = []
        self.list_scopes = []

    def create(self, *, request_type, asset_code, description, requested_by):
        row = {
            "request_code": f"WR-{len(self.created) + 1}", "request_type": request_type, "asset_code": asset_code,
            "description": description, "status": "SUBMITTED", "requested_by": requested_by,
        }
        self.created.append(row)
        return row

    def list_requests(self, *, scope=None):
        self.list_scopes.append(scope)
        return list(self.created)


def _identity(role="PERTAMINA_ENGINEER", scope_type=None, scope_value=None):
    return AuthenticatedIdentity(
        user_id="11111111-1111-1111-1111-111111111111", email="r2@pertamina.test", username="r2", name="R2",
        organization_id="org-pertamina-ru2", organization_code="PERTAMINA_RU_II",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=scope_type, data_scope_value=scope_value,
    )


@pytest.fixture()
def repo():
    repository = _WorkRequestRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: _PumpGateway()
    app.dependency_overrides[get_asset_registry_repository] = lambda: _AssetRegistry()
    app.dependency_overrides[get_work_request_repository] = lambda: repository
    yield repository
    for dep in (get_pump_gateway, get_asset_registry_repository, get_work_request_repository, get_current_user):
        app.dependency_overrides.pop(dep, None)


def _post(identity, request_type, asset_code, description="Seal leak at DE side", **extra):
    app.dependency_overrides[get_current_user] = lambda: identity
    return client.post(
        "/api/ltsa/work-requests",
        json={"request_type": request_type, "asset_code": asset_code, "description": description, **extra},
    )


@pytest.mark.parametrize("request_type", ["PM", "CM", "INSTALLATION"])
def test_in_scope_request_is_allowed_and_server_sets_status_and_requester(repo, request_type):
    res = _post(_identity(scope_type="AREA", scope_value="HCC"), request_type, "104-P-HCC",
                status="CLOSED", requested_by="someone-else", request_code="WR-HACK")
    assert res.status_code == 201, res.text
    row = repo.created[-1]
    assert (row["request_type"], row["asset_code"], row["status"]) == (request_type, "104-P-HCC", "SUBMITTED")
    assert row["requested_by"] == "11111111-1111-1111-1111-111111111111"


@pytest.mark.parametrize("request_type", ["PM", "CM", "INSTALLATION"])
@pytest.mark.parametrize(
    ("scope", "asset"),
    [
        (("AREA", "HCC"), "105-P-OM"),
        (("AREA", "HCC"), "211-P-1A"),
        (("AREA", "OM"), "104-P-HCC"),
        (("AREA", "HOC"), "105-P-OM"),
        (("MA", "MA1"), "104-P-HCC"),
        (("MA", "MA2"), "101-P-HOC"),
        (("MA", "MA3_4"), "101-P-HOC"),
        ((None, None), "104-P-HCC"),
        (("ZONE", "Z1"), "104-P-HCC"),
    ],
)
def test_out_of_scope_or_unscoped_request_is_denied_and_writes_nothing(repo, request_type, scope, asset):
    res = _post(_identity(scope_type=scope[0], scope_value=scope[1]), request_type, asset)
    assert res.status_code == 404
    assert repo.created == []


@pytest.mark.parametrize(
    ("scope", "asset"),
    [
        (("ALL", None), "211-P-1A"),      # raw REAKTOR label: visible to ALL
        (("ALL", None), "701-MM-51"),     # agitator, asset_registry only
        (("MA", "MA3_4"), "105-P-OM"),
        (("MA", "MA1"), "101-P-HOC"),
        (("AREA", "OM"), "105-P-OM"),
    ],
)
def test_requests_follow_all_area_and_ma_scope(repo, scope, asset):
    assert _post(_identity(scope_type=scope[0], scope_value=scope[1]), "CM", asset).status_code == 201


def test_unknown_asset_is_denied_even_for_all_scope(repo):
    assert _post(_identity(scope_type="ALL"), "PM", "999-P-99").status_code == 404
    assert repo.created == []


@pytest.mark.parametrize(
    ("body_type", "description", "status"),
    [("REPAIR", "x", 422), ("PM", "   ", 422)],
)
def test_invalid_request_payload_is_rejected(repo, body_type, description, status):
    assert _post(_identity(scope_type="ALL"), body_type, "104-P-HCC", description=description).status_code == status
    assert repo.created == []


@pytest.mark.parametrize("role", ["PERTAMINA_VIEWER", "TAP_ENGINEER", "TAP_ADMIN", "JOHN_CRANE_ENGINEER", "SUPERUSER"])
@pytest.mark.parametrize("request_type", ["PM", "CM", "INSTALLATION"])
def test_roles_without_the_request_permission_cannot_submit(repo, role, request_type):
    scope = ("AREA", "HCC") if role == "PERTAMINA_VIEWER" else (None, None)
    assert _post(_identity(role=role, scope_type=scope[0], scope_value=scope[1]), request_type, "104-P-HCC").status_code == 403
    assert repo.created == []


def test_request_permissions_are_separate_from_every_write_permission():
    perms = ROLE_PERMISSIONS["PERTAMINA_ENGINEER"]
    assert {"maintenance.request", "installation.request"} <= perms
    for forbidden in ("maintenance.write", "installation.write", "record.edit", "master.edit", "admin.users",
                      "maintenance.admin_review", "maintenance.technical_review", "installation.review"):
        assert forbidden not in perms
    for role in ("SUPERUSER", "TAP_ADMIN", "TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_VIEWER", "BI_READER"):
        assert not ({"maintenance.request", "installation.request"} & ROLE_PERMISSIONS[role]), role


def test_list_is_scope_filtered_by_the_callers_resolved_scope(repo):
    app.dependency_overrides[get_current_user] = lambda: _identity(scope_type="AREA", scope_value="HCC")
    assert client.get("/api/ltsa/work-requests").status_code == 200
    assert repo.list_scopes[-1] == frozenset({"HCC"})
