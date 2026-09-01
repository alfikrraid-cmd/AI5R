"""MWO-LTSA-WHATSAPP-ADMIN-REGISTRATION-001 -- Admin WhatsApp registration
router tests: permission gating (non-admin forbidden, admin allowed) and
the full request/response wiring. Service-level lifecycle edge cases
(idempotency, duplicate binding, inactive user/membership) are covered
in API/TESTS/test_whatsapp_registration_service.py -- not duplicated here.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_auth_repository,
    get_current_user,
    get_record_change_history_repository,
    get_whatsapp_intake_repository,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class _User:
    def __init__(self, status="ACTIVE"):
        self.status = status


class FakeAuthRepository:
    def __init__(self):
        self.users = {"user-1": _User()}
        self.active_memberships = {"user-1"}

    def find_user_by_id(self, user_id):
        return self.users.get(user_id)

    def find_active_membership_for_user(self, user_id):
        return object() if user_id in self.active_memberships else None


class FakeWhatsAppRepository:
    def __init__(self):
        self.rows = {}

    def find_sender_identity_by_hash(self, sender_hash):
        return self.rows.get(sender_hash)

    def create_pending_sender_identity(self, *, sender_hash, user_id, provider):
        self.rows[sender_hash] = {"sender_e164_sha256": sender_hash, "user_id": user_id, "provider": provider, "status": "PENDING"}

    def activate_sender_identity(self, *, sender_hash, user_id):
        self.rows[sender_hash]["status"] = "ACTIVE"


class FakeHistoryRepository:
    def __init__(self):
        self.entries = []

    def append(self, **kwargs):
        self.entries.append(kwargs)
        return kwargs


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role, auth_repo=None, wa_repo=None, history_repo=None):
    app.dependency_overrides[get_current_user] = lambda: _identity(role)
    app.dependency_overrides[get_auth_repository] = lambda: (auth_repo or FakeAuthRepository())
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: (wa_repo or FakeWhatsAppRepository())
    app.dependency_overrides[get_record_change_history_repository] = lambda: (history_repo or FakeHistoryRepository())


class TestPermissionGate:
    def test_tap_engineer_cannot_register(self):
        _override(role="TAP_ENGINEER")
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 403

    def test_pertamina_viewer_cannot_register(self):
        _override(role="PERTAMINA_VIEWER")
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 403

    def test_tap_admin_can_register(self):
        _override(role="TAP_ADMIN")
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "PENDING"

    def test_superuser_can_register(self):
        _override(role="SUPERUSER")
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 200


class TestRegisterThenActivateFlow:
    def test_register_then_activate_reaches_active(self):
        wa_repo = FakeWhatsAppRepository()
        history_repo = FakeHistoryRepository()
        _override(role="TAP_ADMIN", wa_repo=wa_repo, history_repo=history_repo)

        register_response = client.post(
            "/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"}
        )
        assert register_response.status_code == 200
        sender_hash = register_response.json()["data"]["sender_e164_sha256"]

        activate_response = client.post(
            "/api/admin/users/user-1/whatsapp/activate", json={"sender_e164_sha256": sender_hash}
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["data"]["status"] == "ACTIVE"

    def test_unknown_target_user_returns_404(self):
        _override(role="TAP_ADMIN")
        response = client.post("/api/admin/users/ghost-user/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 404

    def test_invalid_phone_number_returns_422(self):
        _override(role="TAP_ADMIN")
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "abc"})
        assert response.status_code == 422
