"""LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- the global password policy, the
password_changed_at parsing used for session invalidation, and
resolve_identity's iat comparison, as pure functions (no FastAPI, no DB)."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.auth_password import (  # noqa: E402
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PasswordPolicyError,
    hash_password,
    validate_password_policy,
)
from API.auth_service import (  # noqa: E402
    AuthenticationError,
    MembershipRecord,
    UserRecord,
    is_route_allowed_during_password_change,
    password_changed_epoch_seconds,
    resolve_identity,
)


# --- Policy ------------------------------------------------------------------


def test_policy_bounds_are_12_to_128():
    assert (PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH) == (12, 128)


@pytest.mark.parametrize("password", ["a" * 12, "Correct horse battery", "x" * 128])
def test_policy_accepts_valid_passwords(password):
    validate_password_policy(password, username="tap.engineer", email="eng@tap.internal")


@pytest.mark.parametrize(
    "password,message",
    [
        (None, "blank"),
        ("", "blank"),
        ("            ", "blank"),
        ("\t\t\t\t\t\t\t\t\t\t\t\t", "blank"),
        ("a" * 11, "at least 12"),
        ("x" * 129, "at most 128"),
        ("tap.engineer.x"[:12], None),
    ],
)
def test_policy_rejects_blank_and_out_of_range(password, message):
    if message is None:
        validate_password_policy(password)  # 12 chars, no identity -> valid
        return
    with pytest.raises(PasswordPolicyError) as error:
        validate_password_policy(password)
    assert message in str(error.value)


@pytest.mark.parametrize("password", ["tap.engineer", "TAP.ENGINEER", "  tap.engineer  "])
def test_policy_rejects_password_equal_to_username(password):
    with pytest.raises(PasswordPolicyError, match="username"):
        validate_password_policy(password, username="tap.engineer", email="eng@tap.internal")


@pytest.mark.parametrize("password", ["eng@tap.internal", "ENG@TAP.INTERNAL"])
def test_policy_rejects_password_equal_to_email(password):
    with pytest.raises(PasswordPolicyError, match="email"):
        validate_password_policy(password, username="tap.engineer", email="eng@tap.internal")


def test_policy_error_is_a_value_error_and_never_echoes_the_password():
    secret = "short-pw-xx"
    with pytest.raises(ValueError) as error:
        validate_password_policy(secret)
    assert secret not in str(error.value)


# --- password_changed_at parsing ---------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-07T03:21:45+00:00",
        "2026-10-07T03:21:45.987654+00:00",
        "2026-10-07T10:21:45+07:00",
        "2026-10-07T03:21:45Z",
        "2026-10-07 03:21:45+00:00",
        "2026-10-07T03:21:45",
        datetime(2026, 10, 7, 3, 21, 45, 500000, tzinfo=timezone.utc),
    ],
)
def test_password_changed_at_parses_to_floor_utc_seconds(value):
    expected = int(datetime(2026, 10, 7, 3, 21, 45, tzinfo=timezone.utc).timestamp())
    assert password_changed_epoch_seconds(value) == expected


@pytest.mark.parametrize("value", [None, ""])
def test_password_changed_at_missing_is_none(value):
    assert password_changed_epoch_seconds(value) is None


# --- resolve_identity iat comparison -----------------------------------------


class _Repo:
    def __init__(self, user):
        self.user = user

    def find_user_by_id(self, user_id):
        return self.user

    def find_membership(self, user_id, organization_id):
        return MembershipRecord(organization_id="org-1", organization_code="TAP", role="TAP_ENGINEER", status="ACTIVE")


def _user(**kw):
    return UserRecord(id="u-1", email="e@tap.internal", password_hash=hash_password("x" * 12), status="ACTIVE", **kw)


def test_iat_before_password_changed_at_is_rejected_same_second_and_later_accepted():
    changed = datetime(2026, 10, 7, 3, 21, 45, 900000, tzinfo=timezone.utc)
    repo = _Repo(_user(password_changed_at=changed.isoformat()))
    floor = int(changed.replace(microsecond=0).timestamp())
    with pytest.raises(AuthenticationError):
        resolve_identity(repo, "u-1", "org-1", token_issued_at=floor - 1)
    assert resolve_identity(repo, "u-1", "org-1", token_issued_at=floor).user_id == "u-1"
    assert resolve_identity(repo, "u-1", "org-1", token_issued_at=floor + 1).user_id == "u-1"


def test_null_password_changed_at_never_rejects():
    repo = _Repo(_user())
    old = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
    assert resolve_identity(repo, "u-1", "org-1", token_issued_at=old).user_id == "u-1"


def test_must_change_password_flows_into_identity():
    assert resolve_identity(_Repo(_user(must_change_password=True)), "u-1", "org-1").must_change_password is True
    assert resolve_identity(_Repo(_user()), "u-1", "org-1").must_change_password is False


# --- Forced-change allowlist ---------------------------------------------------


@pytest.mark.parametrize(
    "method,path,allowed",
    [
        ("GET", "/api/auth/me", True),
        ("get", "/api/auth/me/", True),
        ("POST", "/api/auth/change-password", True),
        ("PATCH", "/api/auth/me", False),
        ("POST", "/api/auth/me", False),
        ("GET", "/api/auth/change-password", False),
        ("GET", "/api/ltsa/pumps", False),
        ("GET", "/api/auth/me/../../ltsa/pumps", False),
        ("GET", "/api/admin/users", False),
    ],
)
def test_forced_change_allowlist_is_exact(method, path, allowed):
    assert is_route_allowed_during_password_change(method, path) is allowed
