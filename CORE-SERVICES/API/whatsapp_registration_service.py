"""MWO-LTSA-WHATSAPP-ADMIN-REGISTRATION-001 -- the ONE admin-controlled
mechanism for binding a WhatsApp number to an existing user identity.

This is deliberately NOT the current "manual SQL insert" workaround: an
admin (admin.users permission, enforced at the router boundary, never
here) links a phone to a user who must already exist, be ACTIVE, and
have an ACTIVE organization membership -- registration never creates a
user, never assigns/changes a role, and never assigns/changes a data
scope. Role/scope remain organization_memberships' own source of truth,
untouched by this module.

Normalization/hashing is reused verbatim from whatsapp_intake_service.py
(normalize_sender_identifier/hash_sender_identifier) -- one canonical
phone->hash mapping, never a second copy that could silently drift from
the request-time auth lookup's own logic.

Lifecycle (no OTP infrastructure exists in this codebase -- Hard Rule:
do not fabricate one): PENDING -> ACTIVE, requiring a second, explicit
administrator action (activate_whatsapp_identity) rather than an
implicit auto-activate on registration. A PENDING row is never resolved
by whatsapp_intake_service.find_identity_by_sender_hash (that query
already filters status = 'ACTIVE'), so a freshly-registered number
cannot be used until an administrator explicitly activates it.

No plaintext phone number is ever persisted or logged here -- only the
SHA256 hash (already computed the same way the inbound auth path
computes it) and, for audit trail entries, a short, irreversible
fingerprint prefix of that hash.
"""

from __future__ import annotations

from typing import Any, Protocol

from .whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier

_PENDING = "PENDING"
_ACTIVE = "ACTIVE"


class WhatsAppRegistrationError(ValueError):
    """Base class for every rejected registration/activation -- the
    router maps each subtype to its own HTTP status, never a bare 500."""


class TargetUserNotFoundError(WhatsAppRegistrationError):
    pass


class TargetUserInactiveError(WhatsAppRegistrationError):
    pass


class TargetMembershipInactiveError(WhatsAppRegistrationError):
    pass


class PhoneAlreadyBoundError(WhatsAppRegistrationError):
    pass


class IdentityNotPendingError(WhatsAppRegistrationError):
    pass


class AuthRepositoryProtocol(Protocol):
    def find_user_by_id(self, user_id: str) -> Any: ...
    def find_active_membership_for_user(self, user_id: str) -> Any: ...


class WhatsAppRegistrationRepositoryProtocol(Protocol):
    def find_sender_identity_by_hash(self, sender_hash: str) -> dict | None: ...
    def create_pending_sender_identity(self, *, sender_hash: str, user_id: str, provider: str) -> None: ...
    def activate_sender_identity(self, *, sender_hash: str, user_id: str) -> None: ...


class HistoryRepositoryProtocol(Protocol):
    def append(
        self,
        *,
        entity_type: str,
        entity_id: str,
        field_name: str,
        old_value: str | None,
        new_value: str | None,
        changed_by: str,
        reason: str,
        source_reference: str | None = None,
    ) -> dict: ...


def _fingerprint(sender_hash: str) -> str:
    # Short, irreversible reference for audit rows -- never the phone
    # number itself, never the full hash (no reason to widen the blast
    # radius of a leaked audit row beyond what a log correlation ID needs).
    return f"wa_hash:{sender_hash[:12]}"


def register_whatsapp_identity(
    *,
    target_user_id: str,
    phone_number: str,
    provider: str,
    actor_id: str,
    auth_repository: AuthRepositoryProtocol,
    whatsapp_repository: WhatsAppRegistrationRepositoryProtocol,
    history_repository: HistoryRepositoryProtocol,
) -> dict:
    user = auth_repository.find_user_by_id(target_user_id)
    if user is None:
        raise TargetUserNotFoundError(f"no user {target_user_id!r}")
    if user.status != "ACTIVE":
        raise TargetUserInactiveError(f"user {target_user_id!r} is not ACTIVE")

    if auth_repository.find_active_membership_for_user(target_user_id) is None:
        raise TargetMembershipInactiveError(f"user {target_user_id!r} has no ACTIVE organization membership")

    normalized = normalize_sender_identifier(phone_number)
    sender_hash = hash_sender_identifier(normalized)

    existing = whatsapp_repository.find_sender_identity_by_hash(sender_hash)
    if existing is not None:
        if existing["user_id"] != target_user_id:
            # Never confirms which OTHER user the number belongs to --
            # the caller only ever learns "already bound elsewhere".
            raise PhoneAlreadyBoundError("This WhatsApp number is already registered to a different user")
        # Idempotent same-user re-registration: no duplicate row, no
        # duplicate audit entry, current status returned as-is.
        return {
            "sender_e164_sha256": sender_hash,
            "user_id": target_user_id,
            "status": existing["status"],
            "no_op": True,
        }

    whatsapp_repository.create_pending_sender_identity(sender_hash=sender_hash, user_id=target_user_id, provider=provider)
    history_repository.append(
        entity_type="WHATSAPP_SENDER_IDENTITY",
        entity_id=target_user_id,
        field_name="status",
        old_value=None,
        new_value=_PENDING,
        changed_by=actor_id,
        reason=f"whatsapp_register provider={provider}",
        source_reference=_fingerprint(sender_hash),
    )
    return {"sender_e164_sha256": sender_hash, "user_id": target_user_id, "status": _PENDING, "no_op": False}


def activate_whatsapp_identity(
    *,
    target_user_id: str,
    sender_e164_sha256: str,
    actor_id: str,
    whatsapp_repository: WhatsAppRegistrationRepositoryProtocol,
    history_repository: HistoryRepositoryProtocol,
) -> dict:
    existing = whatsapp_repository.find_sender_identity_by_hash(sender_e164_sha256)
    if existing is None or existing["user_id"] != target_user_id:
        raise TargetUserNotFoundError("no matching WhatsApp registration for this user/hash")
    if existing["status"] == _ACTIVE:
        return {"sender_e164_sha256": sender_e164_sha256, "user_id": target_user_id, "status": _ACTIVE, "no_op": True}
    if existing["status"] != _PENDING:
        raise IdentityNotPendingError(f"identity status {existing['status']!r} cannot be activated")

    whatsapp_repository.activate_sender_identity(sender_hash=sender_e164_sha256, user_id=target_user_id)
    history_repository.append(
        entity_type="WHATSAPP_SENDER_IDENTITY",
        entity_id=target_user_id,
        field_name="status",
        old_value=_PENDING,
        new_value=_ACTIVE,
        changed_by=actor_id,
        reason="whatsapp_activate",
        source_reference=_fingerprint(sender_e164_sha256),
    )
    return {"sender_e164_sha256": sender_e164_sha256, "user_id": target_user_id, "status": _ACTIVE, "no_op": False}


__all__ = [
    "WhatsAppRegistrationError",
    "TargetUserNotFoundError",
    "TargetUserInactiveError",
    "TargetMembershipInactiveError",
    "PhoneAlreadyBoundError",
    "IdentityNotPendingError",
    "register_whatsapp_identity",
    "activate_whatsapp_identity",
]
