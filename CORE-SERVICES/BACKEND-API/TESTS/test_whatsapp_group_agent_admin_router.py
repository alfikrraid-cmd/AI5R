"""
MWO-LTSA-TAP-GROUP-AGENT-001 Phase 2A -- admin lifecycle router tests.
Uses InMemoryGroupAuthorizationRepository (fast, CI-runnable) behind the
same dependency-override style test_fleet_router.py already establishes
-- the real-Postgres persistence claims themselves are proven separately
in test_whatsapp_group_repository_real_db.py (CORE-SERVICES/API/TESTS),
not re-proven here.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main
from API.auth_service import AuthenticatedIdentity
from API.whatsapp_group_agent_service import hash_group_identifier
from API.whatsapp_group_repository_inmemory import InMemoryGroupAuthorizationRepository
from dependencies import get_current_user, get_group_authorization_repository

ADMIN_IDENTITY = AuthenticatedIdentity(
    user_id="admin-1",
    email="admin@tap.example",
    organization_id="org-1",
    organization_code="TAP",
    role="TAP_ADMIN",
    permissions=frozenset({"admin.users"}),
)
NON_ADMIN_IDENTITY = AuthenticatedIdentity(
    user_id="user-2",
    email="user@tap.example",
    organization_id="org-1",
    organization_code="TAP",
    role="TAP_ENGINEER",
    permissions=frozenset({"maintenance.read"}),
)


@pytest.fixture
def repo():
    return InMemoryGroupAuthorizationRepository()


@pytest.fixture
def client(repo):
    main.app.dependency_overrides[get_group_authorization_repository] = lambda: repo
    main.app.dependency_overrides[get_current_user] = lambda: ADMIN_IDENTITY
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_unauthorized_admin_mutation_denied(repo):
    main.app.dependency_overrides[get_group_authorization_repository] = lambda: repo
    main.app.dependency_overrides[get_current_user] = lambda: NON_ADMIN_IDENTITY
    try:
        response = TestClient(main.app).post(
            "/api/ltsa/whatsapp-group/admin/register",
            json={"group_id": "120363000000000001@g.us", "display_label": "TAP Group"},
        )
        assert response.status_code == 403
    finally:
        main.app.dependency_overrides.clear()


def test_register_creates_pending_group_with_actor_attribution(client, repo):
    response = client.post(
        "/api/ltsa/whatsapp-group/admin/register",
        json={"group_id": "120363000000000002@g.us", "display_label": "TAP Group B"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "PENDING"
    assert body["registered_by"] == "admin-1"
    # never exposes the raw group id
    assert "120363000000000002" not in str(body)


def test_group_cannot_self_activate_via_registration(client):
    response = client.post(
        "/api/ltsa/whatsapp-group/admin/register",
        json={"group_id": "120363000000000003@g.us", "display_label": "TAP Group C"},
    )
    assert response.json()["data"]["status"] == "PENDING"  # never ACTIVE on registration alone


def test_activate_requires_admin_and_records_actor(client):
    group_id = "120363000000000004@g.us"
    client.post("/api/ltsa/whatsapp-group/admin/register", json={"group_id": group_id, "display_label": "D"})
    group_hash = hash_group_identifier(group_id)
    response = client.post(
        "/api/ltsa/whatsapp-group/admin/activate", json={"group_hash": group_hash, "allowed_scope": ["HOC"]}
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "ACTIVE"
    assert body["activated_by"] == "admin-1"
    assert body["allowed_scope"] == ["HOC"]


def test_activate_unknown_group_returns_404(client):
    response = client.post(
        "/api/ltsa/whatsapp-group/admin/activate", json={"group_hash": "does-not-exist"}
    )
    assert response.status_code == 404


def test_disable_requires_admin_and_records_actor(client):
    group_id = "120363000000000005@g.us"
    client.post("/api/ltsa/whatsapp-group/admin/register", json={"group_id": group_id, "display_label": "E"})
    group_hash = hash_group_identifier(group_id)
    client.post("/api/ltsa/whatsapp-group/admin/activate", json={"group_hash": group_hash})
    response = client.post("/api/ltsa/whatsapp-group/admin/disable", json={"group_hash": group_hash})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "DISABLED"
    assert body["disabled_by"] == "admin-1"
