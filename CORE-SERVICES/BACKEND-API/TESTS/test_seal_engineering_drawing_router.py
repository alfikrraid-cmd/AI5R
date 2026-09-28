"""R2B (Mechanical Seal Engineering Drawing + Revision BOM Real Read
Path) -- GET /api/ltsa/seals/{seal_code}/engineering-drawings.

Router-only tests: the repository is faked (no Postgres, no docker --
this workstation has no local DB, and the mission's own DB rule is
explicit: "DO NOT create PostgreSQL"). These prove the route's
contract (path, method, permission gating, argument pass-through,
response shape) -- not that any real drawing/link row exists in
production. That is RUNTIME_VERIFICATION_REQUIRED, reported separately.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app
from dependencies import get_current_user, get_engineering_drawing_repository
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


_SUPERUSER_IDENTITY = _identity("TAP_ADMIN")


class FakeEngineeringDrawingRepository:
    def __init__(self, response=None):
        self.response = response if response is not None else []
        self.calls = []

    def list_drawings_for_seal(self, seal_code, *, scope=None):
        self.calls.append({"seal_code": seal_code, "scope": scope})
        return self.response


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    yield
    app.dependency_overrides.clear()


def test_route_is_registered_get_only():
    openapi = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/seals/{seal_code}/engineering-drawings" in openapi
    assert set(openapi["/api/ltsa/seals/{seal_code}/engineering-drawings"]) == {"get"}


def test_calls_the_repository_with_the_exact_path_seal_code():
    fake = FakeEngineeringDrawingRepository([])
    app.dependency_overrides[get_engineering_drawing_repository] = lambda: fake

    response = client.get("/api/ltsa/seals/SC-101/engineering-drawings")

    assert response.status_code == 200
    assert fake.calls == [{"seal_code": "SC-101", "scope": None}]


def test_returns_the_repositorys_rows_unchanged_inside_a_success_payload():
    rows = [{"drawing_code": "DWG-1", "drawing_number": "211-P-8A-SEAL-01", "title": "Seal Assembly"}]
    fake = FakeEngineeringDrawingRepository(rows)
    app.dependency_overrides[get_engineering_drawing_repository] = lambda: fake

    response = client.get("/api/ltsa/seals/SC-101/engineering-drawings")

    body = response.json()
    assert body["success"] is True
    assert body["data"] == rows


def test_empty_result_is_a_normal_200_with_an_empty_list_not_a_404():
    fake = FakeEngineeringDrawingRepository([])
    app.dependency_overrides[get_engineering_drawing_repository] = lambda: fake

    response = client.get("/api/ltsa/seals/SC-NO-DRAWINGS/engineering-drawings")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_different_seal_code_never_returns_another_seals_cached_rows():
    fake = FakeEngineeringDrawingRepository([{"drawing_code": "DWG-999"}])
    app.dependency_overrides[get_engineering_drawing_repository] = lambda: fake

    client.get("/api/ltsa/seals/SC-101/engineering-drawings")
    client.get("/api/ltsa/seals/SC-102/engineering-drawings")

    # Exact identity per call -- no seal_code caching/reuse across requests.
    assert [call["seal_code"] for call in fake.calls] == ["SC-101", "SC-102"]


def test_a_role_with_seal_read_but_not_drawing_read_is_denied():
    # PERTAMINA_VIEWER has seal.read (this router's own default
    # permission) but NOT drawing.read (the additional, explicit gate
    # this route adds) -- proving the extra dependency actually matters,
    # not just decorative.
    app.dependency_overrides[get_current_user] = lambda: _identity("PERTAMINA_VIEWER")
    fake = FakeEngineeringDrawingRepository([])
    app.dependency_overrides[get_engineering_drawing_repository] = lambda: fake

    response = client.get("/api/ltsa/seals/SC-101/engineering-drawings")

    assert response.status_code == 403
    assert fake.calls == []


def test_a_role_with_both_permissions_is_allowed():
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")
    fake = FakeEngineeringDrawingRepository([])
    app.dependency_overrides[get_engineering_drawing_repository] = lambda: fake

    response = client.get("/api/ltsa/seals/SC-101/engineering-drawings")

    assert response.status_code == 200
    assert len(fake.calls) == 1
