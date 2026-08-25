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
    can_delegate_role,
    decode_access_token,
    issue_access_token,
    permissions_for_role,
    resolve_identity,
    signing_secret,
    normalize_username,
)


class InMemoryAuthRepository:
    """Test double for API.auth_service.AuthRepositoryProtocol."""

    def __init__(self):
        self.users: dict[str, UserRecord] = {}
        self.usernames: dict[str, UserRecord] = {}
        self.memberships: dict[tuple[str, str], MembershipRecord] = {}

    def add_user(
        self,
        user_id: str,
        email: str | None,
        password: str,
        status: str = "ACTIVE",
        username: str | None = None,
    ) -> UserRecord:
        user = UserRecord(
            id=user_id,
            email=email,
            password_hash=hash_password(password),
            status=status,
            username=normalize_username(username) if username is not None else None,
        )
        if email is not None:
            self.users[email.lower()] = user
        if user.username is not None:
            self.usernames[user.username] = user
        return user

    def add_membership(self, user_id: str, organization_id: str, organization_code: str, role: str, status: str = "ACTIVE"):
        self.memberships[(user_id, organization_id)] = MembershipRecord(
            organization_id=organization_id, organization_code=organization_code, role=role, status=status
        )

    def find_user_by_email(self, email):
        return self.users.get(email.lower())

    def find_user_by_username(self, username):
        return self.usernames.get(normalize_username(username))

    def find_user_by_id(self, user_id):
        for user in [*self.users.values(), *self.usernames.values()]:
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


# MWO-LTSA-AUTH-003A-FINAL -- widened from 4 to the final 6 fixed roles.
def test_role_permissions_matrix_covers_exactly_the_v1_fixed_roles():
    assert set(ROLE_PERMISSIONS) == {
        "SUPERUSER", "TAP_ADMIN", "TAP_ENGINEER", "JOHN_CRANE_ENGINEER",
        "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER",
    }


def test_pertamina_viewer_cannot_execute_import():
    assert "import.execute" not in permissions_for_role("PERTAMINA_VIEWER")
    assert "import.read" not in permissions_for_role("PERTAMINA_VIEWER")


def test_pertamina_engineer_cannot_execute_import_either():
    assert "import.execute" not in permissions_for_role("PERTAMINA_ENGINEER")


# MWO-LTSA-AUTH-003A-FINAL -- SUPERUSER also administers users (the
# highest LTSA authority), so "only TAP_ADMIN" is now "only SUPERUSER and
# TAP_ADMIN".
def test_only_superuser_and_tap_admin_have_admin_users_permission():
    for role, permissions in ROLE_PERMISSIONS.items():
        if role in ("SUPERUSER", "TAP_ADMIN"):
            assert "admin.users" in permissions
        else:
            assert "admin.users" not in permissions


def test_only_superuser_has_admin_superuser_and_audit_read_full():
    for role, permissions in ROLE_PERMISSIONS.items():
        if role == "SUPERUSER":
            assert "admin.superuser" in permissions
            assert "audit.read_full" in permissions
        else:
            assert "admin.superuser" not in permissions
            assert "audit.read_full" not in permissions


def test_only_john_crane_engineer_has_technical_review_among_non_superuser_roles():
    for role, permissions in ROLE_PERMISSIONS.items():
        if role in ("SUPERUSER", "JOHN_CRANE_ENGINEER"):
            assert "maintenance.technical_review" in permissions
        else:
            assert "maintenance.technical_review" not in permissions


def test_tap_admin_does_not_get_technical_review_independence_from_tap():
    # Disclosed judgment call: JC's technical review must remain an
    # authority independent of TAP's own chain -- TAP_ADMIN must not be
    # able to self-certify TAP's own PM/CM work.
    assert "maintenance.technical_review" not in permissions_for_role("TAP_ADMIN")


def test_john_crane_engineer_cannot_write_maintenance_or_installation():
    jc = permissions_for_role("JOHN_CRANE_ENGINEER")
    assert "maintenance.write" not in jc
    assert "installation.write" not in jc
    assert "admin.users" not in jc
    assert "admin.superuser" not in jc


def test_john_crane_engineer_can_read_seal_stock_and_internal_component_gpn():
    jc = permissions_for_role("JOHN_CRANE_ENGINEER")
    assert "inventory.read" in jc
    assert "internal_component.read" in jc


def test_pertamina_roles_never_get_internal_component_or_review_permissions():
    for role in ("PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        permissions = permissions_for_role(role)
        for forbidden in (
            "internal_component.read", "internal_inventory.read",
            "maintenance.write", "maintenance.technical_review", "maintenance.admin_review",
            "installation.write", "installation.review",
            "admin.users", "admin.superuser", "audit.read_full",
        ):
            assert forbidden not in permissions, f"{role} must not have {forbidden}"


def test_no_pertamina_role_has_any_write_permission():
    for role in ("PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        assert not any(p.endswith(".write") or p.endswith(".execute") or p.endswith(".edit") for p in permissions_for_role(role))


def test_unknown_role_resolves_to_zero_permissions_never_fabricated():
    assert permissions_for_role("NOT_A_REAL_ROLE") == frozenset()


# MWO-LTSA-AUTH-003A-FINAL -- delegation scope tests.
class TestCanDelegateRole:
    def test_superuser_may_delegate_every_role_including_itself(self):
        for role in ROLE_PERMISSIONS:
            assert can_delegate_role("SUPERUSER", role) is True

    def test_tap_admin_may_delegate_ordinary_operational_roles(self):
        for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
            assert can_delegate_role("TAP_ADMIN", role) is True

    def test_tap_admin_can_never_delegate_superuser(self):
        assert can_delegate_role("TAP_ADMIN", "SUPERUSER") is False


    def test_tap_admin_cannot_delegate_itself_no_self_promotion_chain(self):
        assert can_delegate_role("TAP_ADMIN", "TAP_ADMIN") is False

    def test_non_admin_roles_can_delegate_nothing(self):
        for actor in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
            for target in ROLE_PERMISSIONS:
                assert can_delegate_role(actor, target) is False

    def test_unknown_actor_role_can_delegate_nothing(self):
        assert can_delegate_role("NOT_A_REAL_ROLE", "TAP_ENGINEER") is False


# --- MWO-LTSA-AUTH-001A Task 6: startup secret behavior --------------------


def test_production_with_no_secret_fails_closed(monkeypatch):
    from API.auth_service import AuthConfigurationError

    monkeypatch.delenv("AI5R_AUTH_JWT_SECRET", raising=False)
    monkeypatch.setenv("AI5R_ENV", "production")

    with pytest.raises(AuthConfigurationError):
        signing_secret()


def test_production_with_a_real_secret_succeeds(monkeypatch):
    monkeypatch.setenv("AI5R_ENV", "production")
    monkeypatch.setenv("AI5R_AUTH_JWT_SECRET", "a-real-secret-provided-by-the-deployment-environment")

    assert signing_secret() == "a-real-secret-provided-by-the-deployment-environment"


def test_development_with_no_secret_remains_importable_and_testable(monkeypatch):
    # Ordinary developer/test imports must never require
    # AI5R_AUTH_JWT_SECRET to be set -- only production does. This is not
    # a hardcoded PRODUCTION secret (guarded above by the AI5R_ENV ==
    # "production" branch); it is an explicitly-named, obviously-fake
    # placeholder that can never reach a production deployment.
    monkeypatch.delenv("AI5R_AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("AI5R_ENV", raising=False)

    secret = signing_secret()

    assert secret == "INSECURE-DEV-ONLY-JWT-SECRET-DO-NOT-USE-IN-PRODUCTION"


def test_non_production_env_value_with_no_secret_also_uses_the_dev_fallback(monkeypatch):
    monkeypatch.delenv("AI5R_AUTH_JWT_SECRET", raising=False)
    monkeypatch.setenv("AI5R_ENV", "development")

    assert signing_secret() == "INSECURE-DEV-ONLY-JWT-SECRET-DO-NOT-USE-IN-PRODUCTION"

# --- MWO-AUTH-USERNAME-001: username/email login compatibility -----------


def test_username_login_success():
    repo = InMemoryAuthRepository()
    repo.add_user("user-username", None, "correct-password", username="ravi")
    repo.add_membership("user-username", "org-tap", "TAP", "TAP_ENGINEER")

    token, identity = authenticate(repo, "ravi", "correct-password")

    assert token
    assert identity.user_id == "user-username"
    assert identity.email is None
    assert identity.username == "ravi"


def test_legacy_email_login_success(repository):
    token, identity = authenticate(repository, "engineer@tap.internal", "correct-password")

    assert token
    assert identity.user_id == "user-1"


def test_username_case_insensitive_and_trimmed():
    repo = InMemoryAuthRepository()
    repo.add_user("user-ravi", None, "correct-password", username="ravi")
    repo.add_membership("user-ravi", "org-tap", "TAP", "TAP_ENGINEER")

    token, identity = authenticate(repo, " RAVI ", "correct-password")

    assert token
    assert identity.user_id == "user-ravi"


def test_wrong_password_for_username_is_rejected():
    repo = InMemoryAuthRepository()
    repo.add_user("user-ravi", None, "correct-password", username="ravi")
    repo.add_membership("user-ravi", "org-tap", "TAP", "TAP_ENGINEER")

    with pytest.raises(AuthenticationError):
        authenticate(repo, "ravi", "wrong-password")


def test_unknown_identifier_rejected(repository):
    with pytest.raises(AuthenticationError):
        authenticate(repository, "unknown-user", "anything")


def test_jwt_subject_remains_user_id_for_username_login():
    repo = InMemoryAuthRepository()
    repo.add_user("user-ravi", None, "correct-password", username="ravi")
    repo.add_membership("user-ravi", "org-tap", "TAP", "TAP_ENGINEER")

    token, _identity = authenticate(repo, "ravi", "correct-password")
    payload = decode_access_token(token)

    assert payload["sub"] == "user-ravi"
    assert payload["sub"] != "ravi"


def test_password_scheme_unchanged_for_username_login():
    assert hash_password("correct-password").startswith("scrypt$")