"""
MWO-LTSA-TAP-GROUP-AGENT-001 -- router-boundary tests for the internal
TAP LTSA WhatsApp Group Agent ingress endpoint. Verifies the ingress
secret gate and one authorized end-to-end happy path through FastAPI's
own TestClient (with dependency overrides for every gateway/service, the
same style test_fleet_router.py already establishes) -- the pipeline's
own exhaustive security/behavior matrix lives in
test_whatsapp_group_agent_service.py, not duplicated here.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

import main
from API.auth_service import AuthenticatedIdentity
from API.whatsapp_group_agent_service import hash_group_identifier
from API.whatsapp_group_repository_inmemory import InMemoryGroupAuthorizationRepository
from API.whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier
from dependencies import (
    get_group_authorization_repository,
    get_group_message_rate_limiter,
    get_whatsapp_intake_repository,
)

GROUP_ID = "120363099999999999@g.us"
GROUP_HASH = hash_group_identifier(GROUP_ID)
SENDER_PHONE = "6281234599999"
SENDER_HASH = hash_sender_identifier(normalize_sender_identifier(SENDER_PHONE))


class _AllowAllRateLimiter:
    def allow(self, *, sender_hash: str, group_hash: str) -> bool:
        return True


class _FakeSenderRepository:
    def __init__(self, identity):
        self._identity = identity

    def find_identity_by_sender_hash(self, sender_hash: str):
        return self._identity if sender_hash == SENDER_HASH else None


@pytest.fixture(autouse=True)
def _ingress_secret(monkeypatch):
    monkeypatch.setenv("AI5R_WHATSAPP_GROUP_INGRESS_SECRET", "test-secret-value")
    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def test_missing_ingress_secret_rejected(client):
    response = client.post(
        "/api/ltsa/whatsapp-group/message",
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE,
            "provider_message_id": "wamid.ROUTER-1",
            "text": "/ltsa status 212-P-8A",
        },
    )
    assert response.status_code == 401


def test_wrong_ingress_secret_rejected(client):
    response = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "wrong"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE,
            "provider_message_id": "wamid.ROUTER-2",
            "text": "/ltsa status 212-P-8A",
        },
    )
    assert response.status_code == 401


def test_unconfigured_ingress_secret_returns_503(client, monkeypatch):
    monkeypatch.delenv("AI5R_WHATSAPP_GROUP_INGRESS_SECRET", raising=False)
    response = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "anything"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE,
            "provider_message_id": "wamid.ROUTER-3",
            "text": "/ltsa status 212-P-8A",
        },
    )
    assert response.status_code == 503


def test_non_trigger_message_ignored_end_to_end(client):
    repo = InMemoryGroupAuthorizationRepository()
    repo.register_group(group_hash=GROUP_HASH, display_label="TAP Test", registered_by="admin")
    repo.activate_group(group_hash=GROUP_HASH, activated_by="admin")
    main.app.dependency_overrides[get_group_authorization_repository] = lambda: repo
    main.app.dependency_overrides[get_group_message_rate_limiter] = lambda: _AllowAllRateLimiter()
    main.app.dependency_overrides[get_whatsapp_intake_repository] = lambda: _FakeSenderRepository(None)
    try:
        response = client.post(
            "/api/ltsa/whatsapp-group/message",
            headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
            json={
                "group_id": GROUP_ID,
                "sender_identifier": SENDER_PHONE,
                "provider_message_id": "wamid.ROUTER-4",
                "text": "ordinary chit chat, no trigger here",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "IGNORED_NO_TRIGGER"
        assert body["reply"] is None
    finally:
        main.app.dependency_overrides.clear()


def test_unauthorized_sender_in_active_group_generic_denial_end_to_end(client):
    repo = InMemoryGroupAuthorizationRepository()
    repo.register_group(group_hash=GROUP_HASH, display_label="TAP Test", registered_by="admin")
    repo.activate_group(group_hash=GROUP_HASH, activated_by="admin")
    main.app.dependency_overrides[get_group_authorization_repository] = lambda: repo
    main.app.dependency_overrides[get_group_message_rate_limiter] = lambda: _AllowAllRateLimiter()
    main.app.dependency_overrides[get_whatsapp_intake_repository] = lambda: _FakeSenderRepository(None)
    try:
        response = client.post(
            "/api/ltsa/whatsapp-group/message",
            headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
            json={
                "group_id": GROUP_ID,
                "sender_identifier": SENDER_PHONE,
                "provider_message_id": "wamid.ROUTER-5",
                "text": "/ltsa status 212-P-8A",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "UNAUTHORIZED_SENDER"
        assert body["reply"] == "Nomor Anda belum memiliki akses LTSA."
    finally:
        main.app.dependency_overrides.clear()
