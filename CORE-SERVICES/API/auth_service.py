"""MWO-LTSA-AUTH-001 -- Human Identity + Server Authorization Foundation.

Pure logic layer: token issuance/decoding, the ROLE -> PERMISSIONS
matrix (the ONE canonical mapping this MWO requires -- "Do not scatter
role checks through routers. Endpoints ask for permissions."), and
login/identity-resolution over a duck-typed repository protocol so this
module (and its tests) never depend on a live Postgres connection.
API.auth_repository.AuthRepository is the real, DB-backed
implementation of that same protocol -- swappable in tests for an
in-memory fake, the same "inject the repository, don't hardcode it"
convention API.import_session_repository.py already establishes.

JWT via PyJWT (already installed, added to requirements.txt by this
MWO). Password hashing via API.auth_password (stdlib hashlib.scrypt --
see that module's own header for why no bcrypt/passlib dependency was
added).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

import jwt

from .auth_password import verify_password

_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MINUTES = 30

_GENERIC_LOGIN_FAILURE = "Invalid email or password"


class AuthConfigurationError(RuntimeError):
    """Raised when production authentication configuration is unsafe or
    missing -- see signing_secret()'s own docstring."""


class AuthenticationError(Exception):
    """Any reason a caller is not a valid authenticated identity right
    now: unknown/disabled user, wrong password, no/disabled membership,
    or (via jwt itself) an invalid/tampered/expired token. Always maps
    to HTTP 401 at the router boundary -- never 403 (403 is reserved for
    "authenticated, but lacks this specific permission")."""


# --- ROLE -> PERMISSIONS (the one canonical mapping; MWO's own "Do not
# scatter role checks through routers" rule) -----------------------------
#
# V1 fixed roles only (Decision 4 -- no custom role editor). Granularity
# matches the actual current LTSA router surface (see routers/*.py) --
# master.edit/internal_inventory.read/internal_component.read/admin.users
# are reserved (no current route grants them yet; kept so the matrix
# does not need to change shape when those routes are added later).
#
# Disclosed judgment calls (not specified by the MWO, decided here):
#   - maintenance.write: added beyond the MWO's own suggested minimum
#     set, because real write endpoints exist (POST /work-orders,
#     POST /maintenance) that master.edit (master DATA edit -- pumps/
#     seals canonical definitions, no current route) does not fit.
#   - PERTAMINA_VIEWER vs PERTAMINA_ENGINEER: VIEWER gets baseline asset/
#     inventory/maintenance-history visibility; ENGINEER additionally
#     gets condition.read/drawing.read/engineering_ai.ask (deeper
#     engineering context + AI) -- the MWO names both roles but does not
#     specify the split between them.
#   - Neither Pertamina role gets any *.write permission -- customer
#     visibility rules in this MWO's own frozen decisions are entirely
#     about READ scope; nothing authorizes customer users to create/
#     modify TAP-owned maintenance records.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "TAP_ADMIN": frozenset(
        {
            "pump.read", "seal.read", "inventory.read",
            "maintenance.read", "maintenance.write",
            "condition.read", "drawing.read", "engineering_ai.ask",
            "import.read", "import.execute", "master.edit",
            "internal_inventory.read", "internal_component.read",
            "admin.users",
        }
    ),
    "TAP_ENGINEER": frozenset(
        {
            "pump.read", "seal.read", "inventory.read",
            "maintenance.read", "maintenance.write",
            "condition.read", "drawing.read", "engineering_ai.ask",
            "import.read", "import.execute",
            "internal_inventory.read", "internal_component.read",
        }
    ),
    "PERTAMINA_ENGINEER": frozenset(
        {
            "pump.read", "seal.read", "inventory.read", "maintenance.read",
            "condition.read", "drawing.read", "engineering_ai.ask",
        }
    ),
    "PERTAMINA_VIEWER": frozenset(
        {"pump.read", "seal.read", "inventory.read", "maintenance.read"}
    ),
}


def permissions_for_role(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


# --- JWT ------------------------------------------------------------------


def signing_secret() -> str:
    """NO secret committed to git (this MWO's own rule): read from
    AI5R_AUTH_JWT_SECRET only. In production (AI5R_ENV=production, the
    same env-convention .env.verify.local/.env.production.example
    already use), a missing secret is a configuration error the process
    must refuse to run with -- raised here, and eagerly re-raised at
    application startup (see BACKEND-API/main.py) so a misconfigured
    production deployment fails fast at boot, not silently on the first
    login request. Outside production (local dev/test, where this repo
    has no established convention requiring a real secret), an obviously-
    insecure, hardcoded placeholder is used -- never a real secret, never
    meant to protect anything, exactly the same "dev fallback, never a
    real credential" shape every existing DatabaseConfig default already
    uses (e.g. ltsa_pump_inventory_db_upsert.DatabaseConfig's own
    password="" default)."""
    secret = os.getenv("AI5R_AUTH_JWT_SECRET")
    if secret:
        return secret
    if os.getenv("AI5R_ENV", "development") == "production":
        raise AuthConfigurationError(
            "AI5R_AUTH_JWT_SECRET is not set. Refusing to run production authentication with no signing secret."
        )
    return "INSECURE-DEV-ONLY-JWT-SECRET-DO-NOT-USE-IN-PRODUCTION"


def issue_access_token(user_id: str, organization_id: str) -> str:
    """Token payload is deliberately minimal (sub/org/iat/exp only) --
    role/permissions are never baked in. get_current_user() re-resolves
    them from the repository on every request, so a role change or a
    membership/user being disabled takes effect immediately, not only
    after the (short-lived) token expires."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "org": organization_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, signing_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jwt.InvalidTokenError (or a subclass, e.g. ExpiredSignatureError)
    for a missing/tampered/expired token -- never returns a partial/best-
    effort result. Callers map this to 401."""
    return jwt.decode(token, signing_secret(), algorithms=[_ALGORITHM])


# --- Repository protocol (duck-typed; API.auth_repository.AuthRepository
# is the real Postgres-backed implementation) -------------------------------


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: str
    email: str
    password_hash: str
    status: str


@dataclass(frozen=True, slots=True)
class MembershipRecord:
    organization_id: str
    organization_code: str
    role: str
    status: str


class AuthRepositoryProtocol(Protocol):
    def find_user_by_email(self, email: str) -> UserRecord | None: ...
    def find_user_by_id(self, user_id: str) -> UserRecord | None: ...
    def find_active_membership_for_user(self, user_id: str) -> MembershipRecord | None: ...
    def find_membership(self, user_id: str, organization_id: str) -> MembershipRecord | None: ...


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    user_id: str
    email: str
    organization_id: str
    organization_code: str
    role: str
    permissions: frozenset[str]


def authenticate(repository: AuthRepositoryProtocol, email: str, password: str) -> tuple[str, AuthenticatedIdentity]:
    """POST /api/auth/login's own logic. Unknown user, disabled user, and
    wrong password all raise the SAME generic AuthenticationError message
    -- never disclosing which reason, the standard login-enumeration-
    resistance discipline (a 401 must not tell an attacker whether the
    email exists)."""
    user = repository.find_user_by_email(email)
    if user is None or user.status != "ACTIVE" or not verify_password(password, user.password_hash):
        raise AuthenticationError(_GENERIC_LOGIN_FAILURE)

    membership = repository.find_active_membership_for_user(user.id)
    if membership is None:
        raise AuthenticationError("No active organization membership")

    token = issue_access_token(user.id, membership.organization_id)
    identity = AuthenticatedIdentity(
        user_id=user.id,
        email=user.email,
        organization_id=membership.organization_id,
        organization_code=membership.organization_code,
        role=membership.role,
        permissions=permissions_for_role(membership.role),
    )
    return token, identity


def resolve_identity(repository: AuthRepositoryProtocol, user_id: str, organization_id: str) -> AuthenticatedIdentity:
    """get_current_user()'s own logic, given an already-decoded token's
    sub/org. Re-fetches user AND membership fresh from the repository on
    every call -- a user or membership disabled after the token was
    issued is rejected immediately, never trusted from stale token
    claims (this MWO's own required "membership disabled -> rejected"
    behavior, proven even for a token that has not yet expired)."""
    user = repository.find_user_by_id(user_id)
    if user is None or user.status != "ACTIVE":
        raise AuthenticationError("User is not active")

    membership = repository.find_membership(user_id, organization_id)
    if membership is None or membership.status != "ACTIVE":
        raise AuthenticationError("Organization membership is not active")

    return AuthenticatedIdentity(
        user_id=user.id,
        email=user.email,
        organization_id=membership.organization_id,
        organization_code=membership.organization_code,
        role=membership.role,
        permissions=permissions_for_role(membership.role),
    )


__all__ = [
    "ROLE_PERMISSIONS",
    "permissions_for_role",
    "AuthConfigurationError",
    "AuthenticationError",
    "signing_secret",
    "issue_access_token",
    "decode_access_token",
    "UserRecord",
    "MembershipRecord",
    "AuthRepositoryProtocol",
    "AuthenticatedIdentity",
    "authenticate",
    "resolve_identity",
]
