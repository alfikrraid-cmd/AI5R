import sys
import time
from pathlib import Path

import jwt as pyjwt
import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.auth_password import hash_password  # noqa: E402
from API.auth_service import (  # noqa: E402
    ROLE_PERMISSIONS,
    AuthenticationError,
    MembershipRecord,
    UserRecord,
    authenticate,
    decode_access_token,
    issue_access_token,
    permissions_for_role,
    resolve_identity,
    signing_secret,
)


class InMemoryAuthRepository:
    """Test double for API.auth_service.AuthRepositoryProtocol. Real
    unit tests over real logic (auth_service.py's own authenticate()/
    resolve_identity()), zero database dependency -- matches this MWO's
    own "tests may use explicit test identities" allowance without
    requiring a live Postgres this session has repeatedly found
    unreachable in this environment."""

    def __init__(self):
        self.users: dict[str, UserRecord] = {}
        self.memberships: dict[tuple[str, str], MembershipRecord] = {}

    def add_user(self, user_id: str, email: str, password: str, status: str = "ACTIVE") -> UserRecord:
        user = UserRecord(id=user_id, email=email, password_hash=hash_password(password), status=status)
        self.users[email] = user
        return user

    def add_membership(self, user_id: str, organization_id: str, organization_code: str, role: str, status: str = "ACTIVE"):
        self.memberships[(user_id, organization_id)] = MembershipRecord(
            organization_id=organization_id, organization_code=organization_code, role=role, status=status
        )

    def find_user_by_email(self, email):
        return self.users.get(email)

    def find_user_by_id(self, user_id):
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None

    def find_active_membership_for_user(self, user_id):
        for (uid, _org), membership in self.memberships.items():
            if uid == user_id and membership.status == "ACTIVE":
                return membership
        return None

    def find_membership(self, user_id, organization_id):
        return self.memberships.get((user_id, organization_id))


@pytest.fixture
def repository():
    repo = InMemoryAuthRepository()
    repo.add_user("user-1", "engineer@tap.internal", "correct-password")
    repo.add_membership("user-1", "org-tap", "TAP", "TAP_ENGINEER")
    return repo


# --- 1/2/3/4: login scenarios ------------------------------------------


def test_valid_login_returns_a_token_and_identity(repository):
    token, identity = authenticate(repository, "engineer@tap.internal", "correct-password")
    assert isinstance(token, str) and token
    assert identity.role == "TAP_ENGINEER"
    assert identity.organization_code == "TAP"


def test_wrong_password_is_rejected(repository):
    with pytest.raises(AuthenticationError):
        authenticate(repository, "engineer@tap.internal", "wrong-password")


def test_unknown_user_is_rejected(repository):
    with pytest.raises(AuthenticationError):
        authenticate(repository, "nobody@tap.internal", "anything")


def test_disabled_user_is_rejected(repository):
    repository.add_user("user-2", "disabled@tap.internal", "correct-password", status="DISABLED")
    repository.add_membership("user-2", "org-tap", "TAP", "TAP_ENGINEER")
    with pytest.raises(AuthenticationError):
        authenticate(repository, "disabled@tap.internal", "correct-password")


def test_unknown_user_and_disabled_user_raise_the_same_generic_message(repository):
    # Login-enumeration resistance: a 401 must never disclose whether the
    # email exists.
    repository.add_user("user-2", "disabled@tap.internal", "correct-password", status="DISABLED")
    repository.add_membership("user-2", "org-tap", "TAP", "TAP_ENGINEER")

    unknown_message = None
    disabled_message = None
    try:
        authenticate(repository, "nobody@tap.internal", "x")
    except AuthenticationError as error:
        unknown_message = str(error)
    try:
        authenticate(repository, "disabled@tap.internal", "correct-password")
    except AuthenticationError as error:
        disabled_message = str(error)

    assert unknown_message == disabled_message


def test_login_rejected_when_user_has_no_active_organization_membership(repository):
    repository.add_user("user-3", "orphan@tap.internal", "correct-password")
    with pytest.raises(AuthenticationError):
        authenticate(repository, "orphan@tap.internal", "correct-password")


# --- resolve_identity (get_current_user's own logic) ---------------------


def test_resolve_identity_returns_current_role_and_permissions(repository):
    identity = resolve_identity(repository, "user-1", "org-tap")
    assert identity.role == "TAP_ENGINEER"
    assert identity.permissions == permissions_for_role("TAP_ENGINEER")
    assert "engineering_ai.ask" in identity.permissions


def test_resolve_identity_rejects_disabled_user(repository):
    repository.users["engineer@tap.internal"] = UserRecord(
        id="user-1", email="engineer@tap.internal", password_hash="x", status="DISABLED"
    )
    with pytest.raises(AuthenticationError):
        resolve_identity(repository, "user-1", "org-tap")


def test_resolve_identity_rejects_disabled_membership(repository):
    repository.add_membership("user-1", "org-tap", "TAP", "TAP_ENGINEER", status="DISABLED")
    with pytest.raises(AuthenticationError):
        resolve_identity(repository, "user-1", "org-tap")


def test_resolve_identity_rejects_unknown_membership(repository):
    with pytest.raises(AuthenticationError):
        resolve_identity(repository, "user-1", "org-that-does-not-exist")


# --- JWT -------------------------------------------------------------------


def test_issued_token_decodes_back_to_the_same_subject_and_org():
    token = issue_access_token("user-1", "org-tap")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["org"] == "org-tap"


def test_tampered_token_is_rejected():
    token = issue_access_token("user-1", "org-tap")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_access_token(tampered)


def test_expired_token_is_rejected():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    expired_payload = {"sub": "user-1", "org": "org-tap", "iat": now - timedelta(minutes=60), "exp": now - timedelta(minutes=1)}
    expired_token = pyjwt.encode(expired_payload, signing_secret(), algorithm="HS256")
    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_token_signed_with_a_different_secret_is_rejected():
    forged = pyjwt.encode({"sub": "user-1", "org": "org-tap"}, "a-completely-different-secret", algorithm="HS256")
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_access_token(forged)


# --- ROLE_PERMISSIONS matrix -----------------------------------------------


def test_role_permissions_matrix_covers_exactly_the_v1_fixed_roles():
    assert set(ROLE_PERMISSIONS) == {"TAP_ADMIN", "TAP_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"}


def test_pertamina_viewer_cannot_execute_import():
    assert "import.execute" not in permissions_for_role("PERTAMINA_VIEWER")
    assert "import.read" not in permissions_for_role("PERTAMINA_VIEWER")


def test_pertamina_engineer_cannot_execute_import_either():
    assert "import.execute" not in permissions_for_role("PERTAMINA_ENGINEER")


def test_only_tap_admin_has_admin_users_permission():
    for role, permissions in ROLE_PERMISSIONS.items():
        if role == "TAP_ADMIN":
            assert "admin.users" in permissions
        else:
            assert "admin.users" not in permissions


def test_no_pertamina_role_has_any_write_permission():
    for role in ("PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        assert not any(p.endswith(".write") or p.endswith(".execute") or p.endswith(".edit") for p in permissions_for_role(role))


def test_unknown_role_resolves_to_zero_permissions_never_fabricated():
    assert permissions_for_role("NOT_A_REAL_ROLE") == frozenset()
