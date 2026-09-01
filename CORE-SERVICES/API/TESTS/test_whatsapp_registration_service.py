"""MWO-LTSA-WHATSAPP-ADMIN-REGISTRATION-001 -- whatsapp_registration_service
tests. Pure logic against in-memory fakes -- no DB, no HTTP."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier  # noqa: E402
from API.whatsapp_registration_service import (  # noqa: E402
    IdentityNotPendingError,
    PhoneAlreadyBoundError,
    TargetMembershipInactiveError,
    TargetUserInactiveError,
    TargetUserNotFoundError,
    activate_whatsapp_identity,
    register_whatsapp_identity,
)


class _User:
    def __init__(self, status="ACTIVE"):
        self.status = status


class FakeAuthRepository:
    def __init__(self, *, users=None, active_memberships=None):
        self.users = users or {}
        self.active_memberships = active_memberships or set()

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


def _deps(user_status="ACTIVE", has_membership=True):
    auth_repo = FakeAuthRepository(
        users={"user-1": _User(status=user_status)},
        active_memberships={"user-1"} if has_membership else set(),
    )
    return auth_repo, FakeWhatsAppRepository(), FakeHistoryRepository()


class TestRegisterWhatsAppIdentity:
    def test_unknown_target_user_is_rejected(self):
        auth_repo, wa_repo, history = _deps()
        with pytest.raises(TargetUserNotFoundError):
            register_whatsapp_identity(
                target_user_id="ghost", phone_number="0812345678", provider="whatsapp_cloud",
                actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
            )

    def test_inactive_user_is_rejected(self):
        auth_repo, wa_repo, history = _deps(user_status="DISABLED")
        with pytest.raises(TargetUserInactiveError):
            register_whatsapp_identity(
                target_user_id="user-1", phone_number="0812345678", provider="whatsapp_cloud",
                actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
            )

    def test_inactive_membership_is_rejected(self):
        auth_repo, wa_repo, history = _deps(has_membership=False)
        with pytest.raises(TargetMembershipInactiveError):
            register_whatsapp_identity(
                target_user_id="user-1", phone_number="0812345678", provider="whatsapp_cloud",
                actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
            )

    def test_admin_caller_registers_new_number_as_pending(self):
        auth_repo, wa_repo, history = _deps()
        result = register_whatsapp_identity(
            target_user_id="user-1", phone_number="081234567890", provider="whatsapp_cloud",
            actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
        )
        assert result["status"] == "PENDING"
        assert result["no_op"] is False
        assert len(history.entries) == 1
        assert history.entries[0]["new_value"] == "PENDING"
        assert history.entries[0]["changed_by"] == "admin-1"
        # No plaintext phone anywhere in the audit entry.
        for value in history.entries[0].values():
            assert "081234567890" not in str(value)

    def test_duplicate_same_user_registration_is_idempotent(self):
        auth_repo, wa_repo, history = _deps()
        register_whatsapp_identity(
            target_user_id="user-1", phone_number="081234567890", provider="whatsapp_cloud",
            actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
        )
        result = register_whatsapp_identity(
            target_user_id="user-1", phone_number="6281234567890", provider="whatsapp_cloud",
            actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
        )
        assert result["no_op"] is True
        assert len(history.entries) == 1  # no duplicate audit entry

    def test_phone_already_bound_to_different_user_is_rejected(self):
        auth_repo, wa_repo, history = _deps()
        auth_repo.users["user-2"] = _User(status="ACTIVE")
        auth_repo.active_memberships.add("user-2")
        register_whatsapp_identity(
            target_user_id="user-1", phone_number="081234567890", provider="whatsapp_cloud",
            actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
        )
        with pytest.raises(PhoneAlreadyBoundError):
            register_whatsapp_identity(
                target_user_id="user-2", phone_number="+6281234567890", provider="whatsapp_cloud",
                actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
            )

    def test_invalid_phone_number_raises_value_error(self):
        auth_repo, wa_repo, history = _deps()
        with pytest.raises(ValueError):
            register_whatsapp_identity(
                target_user_id="user-1", phone_number="abc", provider="whatsapp_cloud",
                actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
            )


class TestActivateWhatsAppIdentity:
    def test_activate_pending_moves_to_active_and_audits(self):
        auth_repo, wa_repo, history = _deps()
        registered = register_whatsapp_identity(
            target_user_id="user-1", phone_number="081234567890", provider="whatsapp_cloud",
            actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
        )
        result = activate_whatsapp_identity(
            target_user_id="user-1", sender_e164_sha256=registered["sender_e164_sha256"],
            actor_id="admin-2", whatsapp_repository=wa_repo, history_repository=history,
        )
        assert result["status"] == "ACTIVE"
        assert result["no_op"] is False
        assert len(history.entries) == 2
        assert history.entries[1]["old_value"] == "PENDING"
        assert history.entries[1]["new_value"] == "ACTIVE"

    def test_activate_already_active_is_idempotent(self):
        auth_repo, wa_repo, history = _deps()
        registered = register_whatsapp_identity(
            target_user_id="user-1", phone_number="081234567890", provider="whatsapp_cloud",
            actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
        )
        activate_whatsapp_identity(
            target_user_id="user-1", sender_e164_sha256=registered["sender_e164_sha256"],
            actor_id="admin-1", whatsapp_repository=wa_repo, history_repository=history,
        )
        result = activate_whatsapp_identity(
            target_user_id="user-1", sender_e164_sha256=registered["sender_e164_sha256"],
            actor_id="admin-1", whatsapp_repository=wa_repo, history_repository=history,
        )
        assert result["no_op"] is True
        assert len(history.entries) == 2  # no third audit entry

    def test_activate_unknown_registration_is_rejected(self):
        _, wa_repo, history = _deps()
        with pytest.raises(TargetUserNotFoundError):
            activate_whatsapp_identity(
                target_user_id="user-1",
                sender_e164_sha256=hash_sender_identifier(normalize_sender_identifier("0812000000")),
                actor_id="admin-1", whatsapp_repository=wa_repo, history_repository=history,
            )

    def test_activate_revoked_identity_is_rejected(self):
        auth_repo, wa_repo, history = _deps()
        registered = register_whatsapp_identity(
            target_user_id="user-1", phone_number="081234567890", provider="whatsapp_cloud",
            actor_id="admin-1", auth_repository=auth_repo, whatsapp_repository=wa_repo, history_repository=history,
        )
        wa_repo.rows[registered["sender_e164_sha256"]]["status"] = "REVOKED"
        with pytest.raises(IdentityNotPendingError):
            activate_whatsapp_identity(
                target_user_id="user-1", sender_e164_sha256=registered["sender_e164_sha256"],
                actor_id="admin-1", whatsapp_repository=wa_repo, history_repository=history,
            )
