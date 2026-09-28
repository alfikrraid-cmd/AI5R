"""LTSA_POWER_BI_R1C -- Dedicated Machine Basic Authentication & Scrypt Hashing.

Provisions machine identity for unattended Power BI Desktop and Service
scheduled cloud refresh.

Security & Architecture Guarantees:
1. Canonical Hash Storage: scrypt$16384$8$1$<salt_hex>$<hash_hex>
   Stores complete self-describing scrypt parameters + salt + hash.
   No separate salt columns.
2. Constant-time secret comparison via hmac.compare_digest.
3. Timing oracle mitigation: if client_id does not exist, a full scrypt
   verification is computed against a dummy hash before raising 401.
4. Structurally confined to role BI_READER and permission bi.read.
5. Zero plaintext persistence: client_secret is generated and displayed
   exactly ONCE on create/rotate.
6. Zero header logging: Authorization headers are never logged.
7. Supports dual-hash zero-downtime overlapping rotation with grace expiry.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .auth_service import AuthenticatedIdentity, AuthenticationError

logger = logging.getLogger("ltsa.bi_machine_auth")

_SCHEME = "scrypt"
_DEFAULT_N = 16384  # 2^14 CPU/memory cost
_DEFAULT_R = 8      # block size
_DEFAULT_P = 1      # parallelization
_SALT_BYTES = 16    # 128-bit salt
_DKLEN = 32         # 256-bit output key

_CLIENT_ID_PATTERN = re.compile(r"^ltsa_bi_[a-f0-9]{24}$")
_GENERIC_AUTH_FAILURE = "Invalid credentials"


def hash_secret(secret: str) -> str:
    """Computes canonical scrypt hash representation:
    scrypt$16384$8$1$<salt_hex>$<hash_hex>"""
    if not secret:
        raise ValueError("secret must not be empty")

    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        secret.encode("utf-8"),
        salt=salt,
        n=_DEFAULT_N,
        r=_DEFAULT_R,
        p=_DEFAULT_P,
        dklen=_DKLEN,
    )
    return f"{_SCHEME}${_DEFAULT_N}${_DEFAULT_R}${_DEFAULT_P}${salt.hex()}${derived.hex()}"


def verify_secret(secret: str, encoded: str) -> bool:
    """Verifies a secret against a canonical scrypt string.
    Uses hmac.compare_digest for constant-time comparison.
    Never raises on malformed input."""
    if not secret or not encoded:
        return False
    try:
        scheme, n, r, p, salt_hex, hash_hex = encoded.split("$")
        if scheme != _SCHEME:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        candidate = hashlib.scrypt(
            secret.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)


def generate_client_id() -> str:
    """Generates a structured machine client ID with 96 bits of entropy:
    ltsa_bi_<24 hex characters>"""
    return f"ltsa_bi_{secrets.token_hex(12)}"


def generate_client_secret() -> str:
    """Generates a secure client secret with >= 256 bits of entropy:
    sec_<48 URL-safe characters>"""
    return f"sec_{secrets.token_urlsafe(36)}"


# Pre-computed dummy hash to mitigate timing side-channel when client_id is unknown
_DUMMY_SCRYPT_HASH = hash_secret("dummy-timing-oracle-mitigation-fixed-secret")


@dataclass(frozen=True)
class BiMachineCredentialRecord:
    id: str
    client_id: str
    description: str | None
    organization_id: str
    organization_code: str
    role: str
    primary_secret_hash: str
    primary_created_at: datetime
    secondary_secret_hash: str | None
    secondary_created_at: datetime | None
    secondary_expires_at: datetime | None
    status: str
    revoked_at: datetime | None
    revoked_by: str | None
    revocation_reason: str | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BiMachineCredentialRepositoryProtocol(Protocol):
    def get_credential_by_client_id(self, client_id: str) -> BiMachineCredentialRecord | None: ...
    def create_credential(
        self,
        client_id: str,
        secret_hash: str,
        organization_id: str,
        description: str | None,
        actor: str,
    ) -> BiMachineCredentialRecord: ...
    def rotate_credential(
        self,
        client_id: str,
        new_secret_hash: str,
        grace_days: int,
        actor: str,
    ) -> BiMachineCredentialRecord: ...
    def promote_secondary_secret(
        self,
        client_id: str,
        actor: str,
    ) -> BiMachineCredentialRecord: ...
    def revoke_credential(
        self,
        client_id: str,
        reason: str,
        actor: str,
    ) -> BiMachineCredentialRecord: ...
    def record_audit_event(
        self,
        client_id: str,
        event_type: str,
        actor: str,
        credential_id: str | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None: ...
    def record_last_used(self, client_id: str) -> None: ...
    def list_credentials(self) -> list[BiMachineCredentialRecord]: ...


def _mask_client_id(client_id: str) -> str:
    if len(client_id) <= 12:
        return "***"
    return f"{client_id[:10]}...{client_id[-4:]}"


def authenticate_basic_credentials(
    client_id: str,
    secret: str,
    repository: BiMachineCredentialRepositoryProtocol,
    source_ip: str | None = None,
    user_agent: str | None = None,
) -> AuthenticatedIdentity:
    """Authenticates a Power BI machine credential from Basic Auth.
    Enforces status, expiration, scrypt verification, role BI_READER,
    and returns AuthenticatedIdentity with bi.read permission.
    Always returns uniform AuthenticationError on failure."""
    masked_id = _mask_client_id(client_id) if client_id else "unknown"

    credential = repository.get_credential_by_client_id(client_id)
    if credential is None:
        # Run dummy verification to ensure constant time execution
        verify_secret(secret, _DUMMY_SCRYPT_HASH)
        logger.warning(
            "BI_AUTH_FAILURE client_id=%s reason=UNKNOWN_CLIENT_ID ip=%s",
            masked_id,
            source_ip or "unknown",
        )
        raise AuthenticationError(_GENERIC_AUTH_FAILURE)

    # 1. Status check
    if credential.status != "ACTIVE":
        verify_secret(secret, _DUMMY_SCRYPT_HASH)
        logger.warning(
            "BI_AUTH_FAILURE client_id=%s reason=INACTIVE_OR_REVOKED status=%s ip=%s",
            masked_id,
            credential.status,
            source_ip or "unknown",
        )
        raise AuthenticationError(_GENERIC_AUTH_FAILURE)

    # 2. Secret verification (primary first, then secondary with grace window)
    authenticated = False
    used_secondary = False

    if verify_secret(secret, credential.primary_secret_hash):
        authenticated = True
    elif credential.secondary_secret_hash:
        now = datetime.now(timezone.utc)
        sec_expires = credential.secondary_expires_at
        if sec_expires is not None and sec_expires.tzinfo is None:
            sec_expires = sec_expires.replace(tzinfo=timezone.utc)

        if sec_expires is not None and now > sec_expires:
            logger.warning(
                "BI_AUTH_FAILURE client_id=%s reason=SECONDARY_SECRET_EXPIRED ip=%s",
                masked_id,
                source_ip or "unknown",
            )
            raise AuthenticationError(_GENERIC_AUTH_FAILURE)

        if verify_secret(secret, credential.secondary_secret_hash):
            authenticated = True
            used_secondary = True

    if not authenticated:
        logger.warning(
            "BI_AUTH_FAILURE client_id=%s reason=INVALID_SECRET ip=%s",
            masked_id,
            source_ip or "unknown",
        )
        raise AuthenticationError(_GENERIC_AUTH_FAILURE)

    # 3. Structural role verification
    if credential.role != "BI_READER":
        logger.error(
            "BI_AUTH_CRITICAL_ROLE_VIOLATION client_id=%s illegal_role=%s",
            masked_id,
            credential.role,
        )
        raise AuthenticationError(_GENERIC_AUTH_FAILURE)

    # 4. Record usage & log auth success
    try:
        repository.record_last_used(client_id)
    except Exception:
        logger.warning("Failed to record last_used for client_id=%s", masked_id)

    logger.info(
        "BI_AUTH_SUCCESS client_id=%s org=%s secondary=%s ip=%s",
        masked_id,
        credential.organization_code,
        used_secondary,
        source_ip or "unknown",
    )

    return AuthenticatedIdentity(
        user_id=credential.id,
        email=None,
        organization_id=credential.organization_id,
        organization_code=credential.organization_code,
        role="BI_READER",
        permissions=frozenset({"bi.read"}),
        username=credential.client_id,
        name=credential.description or credential.client_id,
    )
