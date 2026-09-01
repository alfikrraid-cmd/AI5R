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


class FakeMembership:
    def __init__(self, organization_id, status="ACTIVE"):
        self.organization_id = organization_id
        self.status = status


class FakeAuthRepository:
    # memberships: dict[user_id, list[FakeMembership]] -- list ORDER
    # matters: index 0 is the earliest-created membership, matching
    # find_active_membership_for_user's real "ORDER BY created_at ASC
    # LIMIT 1" canonical-membership convention (auth_repository.py) --
    # a multi-membership target's LATER memberships (even if ACTIVE, even
    # in the actor's own org) must never be used to authorize.
    def __init__(self, *, memberships=None):
        self.users = {"user-1": _User()}
        self.memberships = memberships if memberships is not None else {"user-1": [FakeMembership("org-tap")]}

    def find_user_by_id(self, user_id):
        return self.users.get(user_id)

    def find_active_membership_for_user(self, user_id):
        for membership in self.memberships.get(user_id, []):
            if membership.status == "ACTIVE":
                return membership
        return None


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


class TestOrganizationBoundary:
    # Actor identity is always organization_id="org-tap" (see _identity()).

    def test_tap_admin_same_org_active_memberships_registers_successfully(self):
        auth_repo = FakeAuthRepository(memberships={"user-1": [FakeMembership("org-tap")]})
        _override(role="TAP_ADMIN", auth_repo=auth_repo)
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 200

    def test_tap_admin_cross_org_register_is_forbidden(self):
        auth_repo = FakeAuthRepository(memberships={"user-1": [FakeMembership("org-other")]})
        _override(role="TAP_ADMIN", auth_repo=auth_repo)
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 403

    def test_tap_admin_cross_org_activate_is_forbidden(self):
        auth_repo = FakeAuthRepository(memberships={"user-1": [FakeMembership("org-tap")]})
        wa_repo = FakeWhatsAppRepository()
        history_repo = FakeHistoryRepository()
        _override(role="TAP_ADMIN", auth_repo=auth_repo, wa_repo=wa_repo, history_repo=history_repo)
        registered = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert registered.status_code == 200
        sender_hash = registered.json()["data"]["sender_e164_sha256"]

        # Actor's own org membership is unchanged; target's canonical
        # organization changes to a different one before activation.
        auth_repo.memberships["user-1"] = [FakeMembership("org-other")]
        response = client.post("/api/admin/users/user-1/whatsapp/activate", json={"sender_e164_sha256": sender_hash})
        assert response.status_code == 403

    def test_tap_admin_target_inactive_membership_is_rejected(self):
        auth_repo = FakeAuthRepository(memberships={"user-1": [FakeMembership("org-tap", status="DISABLED")]})
        _override(role="TAP_ADMIN", auth_repo=auth_repo)
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        # No active membership at all -- org-boundary check is skipped
        # (nothing to compare against); whatsapp_registration_service's
        # own TargetMembershipInactiveError rejects it (404), same as
        # every other "target has no active membership" path already
        # established in this router (see reset_password above).
        assert response.status_code == 404

    def test_superuser_bypasses_organization_boundary(self):
        auth_repo = FakeAuthRepository(memberships={"user-1": [FakeMembership("org-other")]})
        _override(role="SUPERUSER", auth_repo=auth_repo)
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 200

    def test_multi_membership_target_uses_only_canonical_membership_no_leakage(self):
        # Canonical (earliest-created) membership is org-other; a LATER
        # active membership in the actor's own org-tap must NOT be used
        # to authorize the actor -- proves no cross-membership leakage.
        auth_repo = FakeAuthRepository(
            memberships={"user-1": [FakeMembership("org-other"), FakeMembership("org-tap")]}
        )
        _override(role="TAP_ADMIN", auth_repo=auth_repo)
        response = client.post("/api/admin/users/user-1/whatsapp/register", json={"phone_number": "081234567890"})
        assert response.status_code == 403
