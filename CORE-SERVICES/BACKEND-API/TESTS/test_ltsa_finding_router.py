"""MWO-LTSA-REPORTING-R4 -- ltsa_finding router tests: RBAC (read/write/
area-MA), request/response shape, and repository-exception -> HTTP-status
mapping. Fake repository, same style as test_pm_occurrence_write_router.py
-- NOT `from main import app` (this router is deliberately not wired into
main.py yet, see routers/ltsa_finding.py's own header), a standalone
FastAPI app mounting just this router instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from routers import ltsa_finding as router_module  # noqa: E402
from dependencies import get_current_user  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.ltsa_finding_repository import (  # noqa: E402
    AssetMismatch,
    ClosedRequiresClosedDate,
    InvalidSourceDomain,
    SourceRecordNotFound,
)

app = FastAPI()
app.include_router(router_module.router)
client = TestClient(app)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None, user_id="actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


class FakeLtsaFindingRepository:
    def __init__(self):
        self.calls: list[tuple] = []
        self._findings = {}
        self._raise_on_create: Exception | None = None

    def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        if self._raise_on_create:
            raise self._raise_on_create
        row = {"finding_code": "LTSAFND-NEW", "status": None, "severity": None, **kwargs}
        self._findings["LTSAFND-NEW"] = row
        return row

    def update(self, code, **kwargs):
        self.calls.append(("update", code, kwargs))
        if code not in self._findings:
            return None
        self._findings[code] = {**self._findings[code], **kwargs.get("values", {})}
        return self._findings[code]

    def find_by_code_with_area(self, code):
        self.calls.append(("find_by_code_with_area", code))
        if code == "LTSAFND-MISSING":
            return None
        return {"finding_code": code, "asset_code": "211-P-13AR", "asset_area": "HOC", "status": None, "severity": None}

    def list_findings(self, **kwargs):
        self.calls.append(("list_findings", kwargs))
        return {"success": True, "data": [], "items": [], "count": 0, "total": 0, "limit": kwargs.get("limit", 25), "offset": kwargs.get("offset", 0)}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role: str, *, repository=None, **identity_kwargs):
    fake = repository or FakeLtsaFindingRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, **identity_kwargs)
    app.dependency_overrides[router_module.get_ltsa_finding_repository] = lambda: fake
    return fake


# ---- RBAC read ----

def test_role_without_condition_read_denied_list():
    _override("PERTAMINA_VIEWER")  # no condition.read
    response = client.get("/api/ltsa/findings")
    assert response.status_code == 403


def test_role_with_condition_read_allowed_list():
    _override("PERTAMINA_ENGINEER")
    response = client.get("/api/ltsa/findings")
    assert response.status_code == 200


# ---- RBAC write ----

def test_role_without_maintenance_write_denied_create():
    _override("PERTAMINA_ENGINEER")  # condition.read yes, maintenance.write no
    response = client.post(
        "/api/ltsa/findings",
        json={"source_domain": "PM_OCCURRENCE", "source_record_code": "PMOCC-1", "finding_text": "x"},
    )
    assert response.status_code == 403


def test_role_with_maintenance_write_allowed_create():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/findings",
        json={"source_domain": "PM_OCCURRENCE", "source_record_code": "PMOCC-1", "finding_text": "x"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["finding_code"] == "LTSAFND-NEW"


# ---- area/MA restriction ----

def test_area_restricted_identity_cannot_see_finding_outside_scope():
    fake = FakeLtsaFindingRepository()
    _override("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA3", repository=fake)  # MA3 != HOC
    response = client.get("/api/ltsa/findings/LTSAFND-1")
    assert response.status_code == 404


def test_area_restricted_identity_can_see_finding_inside_scope():
    fake = FakeLtsaFindingRepository()
    _override("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA1", repository=fake)  # MA1 includes HOC
    response = client.get("/api/ltsa/findings/LTSAFND-1")
    assert response.status_code == 200


def test_finding_not_found():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/findings/LTSAFND-MISSING")
    assert response.status_code == 404


# ---- exception -> HTTP status mapping ----

def test_invalid_source_domain_returns_400():
    fake = FakeLtsaFindingRepository()
    fake._raise_on_create = InvalidSourceDomain("CM_REPORT")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post(
        "/api/ltsa/findings",
        json={"source_domain": "CM_REPORT", "source_record_code": "X", "finding_text": "x"},
    )
    assert response.status_code == 400


def test_nonexistent_source_returns_404():
    fake = FakeLtsaFindingRepository()
    fake._raise_on_create = SourceRecordNotFound("PM_OCCURRENCE:PMOCC-999")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post(
        "/api/ltsa/findings",
        json={"source_domain": "PM_OCCURRENCE", "source_record_code": "PMOCC-999", "finding_text": "x"},
    )
    assert response.status_code == 404


def test_asset_mismatch_returns_409():
    fake = FakeLtsaFindingRepository()
    fake._raise_on_create = AssetMismatch("mismatch")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post(
        "/api/ltsa/findings",
        json={"source_domain": "PM_OCCURRENCE", "source_record_code": "PMOCC-1", "asset_code": "X", "finding_text": "x"},
    )
    assert response.status_code == 409


def test_closed_requires_closed_date_returns_400_on_create():
    fake = FakeLtsaFindingRepository()
    fake._raise_on_create = ClosedRequiresClosedDate("needs closed_date")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post(
        "/api/ltsa/findings",
        json={"source_domain": "PM_OCCURRENCE", "source_record_code": "PMOCC-1", "finding_text": "x", "status": "CLOSED"},
    )
    assert response.status_code == 400


# ---- update ----

def test_update_not_found_returns_404():
    _override("TAP_ENGINEER")
    response = client.patch("/api/ltsa/findings/LTSAFND-DOES-NOT-EXIST", json={"finding_text": "x"})
    assert response.status_code == 404


def test_update_actor_is_server_controlled_not_client_supplied():
    fake = FakeLtsaFindingRepository()
    fake._findings["LTSAFND-1"] = {"finding_code": "LTSAFND-1", "status": None, "severity": None}
    _override("TAP_ENGINEER", repository=fake, user_id="real-actor")
    response = client.patch("/api/ltsa/findings/LTSAFND-1", json={"finding_text": "new"})
    assert response.status_code == 200
    _, code, kwargs = fake.calls[-1]
    assert kwargs["updated_by"] == "real-actor"
