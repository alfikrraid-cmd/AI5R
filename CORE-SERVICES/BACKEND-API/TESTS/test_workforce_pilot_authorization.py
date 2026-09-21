"""Test-only routes exercise production pilot gates; no executor is mounted."""
import sys
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

for path in (Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[2]):
    sys.path.insert(0, str(path))

from API.auth_service import AuthenticatedIdentity, ROLE_PERMISSIONS
from dependencies import get_current_user
from routers.workforce import require_pilot_execute, require_pilot_review


def identity(permissions, role="TAP_ENGINEER"):
    return AuthenticatedIdentity(
        user_id="server-user", email=None, organization_id="test-org",
        organization_code="TAP", role=role, permissions=frozenset(permissions),
    )


@pytest.fixture
def app():
    application = FastAPI()

    @application.post("/execute")
    def execute(payload: dict, actor=Depends(require_pilot_execute)):
        return {"actor_id": actor.user_id}

    @application.post("/review")
    def review(payload: dict, actor=Depends(require_pilot_review)):
        return {"reviewer_id": actor.user_id}

    return application


@pytest.mark.parametrize("action", ["execute", "review"])
def test_anonymous_rejected(app, action):
    assert TestClient(app).post(f"/{action}", json={}).status_code == 401


@pytest.mark.parametrize("action", ["execute", "review"])
@pytest.mark.parametrize("grant", [None, "execute", "review"])
def test_permissions_independent(app, action, grant):
    permissions = [] if grant is None else [f"workforce.pilot.{grant}"]
    app.dependency_overrides[get_current_user] = lambda: identity(permissions)
    response = TestClient(app).post(f"/{action}", json={})
    assert response.status_code == (200 if action == grant else 403)


@pytest.mark.parametrize("action", ["execute", "review"])
@pytest.mark.parametrize("spoof", [
    {"role": "SUPERUSER"}, {"is_human": True}, {"chief": True},
    {"reviewer": "attacker", "reviewer_id": "attacker", "username": "attacker"},
])
def test_payload_cannot_elevate_or_replace_identity(app, action, spoof):
    app.dependency_overrides[get_current_user] = lambda: identity([])
    client = TestClient(app)
    assert client.post(f"/{action}", json=spoof).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: identity([f"workforce.pilot.{action}"])
    result = client.post(f"/{action}", json=spoof)
    assert result.status_code == 200
    assert list(result.json().values()) == ["server-user"]


@pytest.mark.parametrize("action", ["execute", "review"])
def test_superuser_uses_explicit_grants_without_role_bypass(app, action):
    app.dependency_overrides[get_current_user] = lambda: identity([], "SUPERUSER")
    client = TestClient(app)
    assert client.post(f"/{action}", json={}).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: identity(ROLE_PERMISSIONS["SUPERUSER"], "SUPERUSER")
    assert client.post(f"/{action}", json={}).status_code == 200
    for role, permissions in ROLE_PERMISSIONS.items():
        assert (f"workforce.pilot.{action}" in permissions) == (role == "SUPERUSER")
