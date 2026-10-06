import hashlib
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.auth_password import hash_password, verify_password
from API.auth_service import UserRecord, normalize_username
from API.password_reset_repository import FakePasswordResetRepository
from API.password_reset_service import (
    InvalidTokenError,
    PasswordResetRateLimiter,
    PasswordResetService,
    RateLimitExceededError,
)
from API.resend_client import ResendClient, ResendConfig, ResendResult


class InMemoryAuthRepository:
    def __init__(self):
        self.users: dict[str, UserRecord] = {}
        self.usernames: dict[str, UserRecord] = {}

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

    def find_user_by_email(self, email: str) -> UserRecord | None:
        return self.users.get((email or "").lower())

    def find_user_by_username(self, username: str) -> UserRecord | None:
        return self.usernames.get((username or "").lower())

    def find_user_by_id(self, user_id: str) -> UserRecord | None:
        for u in list(self.users.values()) + list(self.usernames.values()):
            if u.id == user_id:
                return u
        return None

    def update_password_hash(
        self,
        user_id: str,
        password_hash: str,
        *,
        updated_by: str,
        must_change_password: bool | None = None,
        password_changed_at=None,
    ) -> None:
        for u in list(self.users.values()) + list(self.usernames.values()):
            if u.id == user_id:
                new_record = UserRecord(
                    id=u.id,
                    email=u.email,
                    password_hash=password_hash,
                    status=u.status,
                    username=u.username,
                    must_change_password=(
                        u.must_change_password if must_change_password is None else must_change_password
                    ),
                    password_changed_at=(
                        password_changed_at.isoformat() if password_changed_at is not None else u.password_changed_at
                    ),
                )
                if u.email is not None:
                    self.users[u.email.lower()] = new_record
                if u.username is not None:
                    self.usernames[u.username] = new_record
                return


@pytest.fixture
def auth_repo():
    repo = InMemoryAuthRepository()
    repo.add_user("user-1", "engineer@tap.com", "OldPassword123", username="tap_engineer")
    repo.add_user("user-2", None, "NoEmailPass123", username="no_email_user")
    repo.add_user("user-3", "inactive@tap.com", "InactivePass123", status="INACTIVE", username="inactive_user")
    return repo


@pytest.fixture
def reset_repo():
    return FakePasswordResetRepository()


@pytest.fixture
def mock_resend_client():
    client = ResendClient(
        ResendConfig(
            api_key="re_mock_test_key",
            app_public_url="https://osa-system.com",
            from_email="noreply@mail.osa-system.com",
            from_name="AI5R LTSA",
        )
    )
    client.send_email = MagicMock(return_value=ResendResult(status="SUCCESS", email_id="msg-123"))
    return client


def test_forgot_password_existing_active_email(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    service.request_password_reset("engineer@tap.com", client_ip="192.168.1.1")

    # Resend was called
    assert mock_resend_client.send_email.call_count == 1
    call_args = mock_resend_client.send_email.call_args[1]
    assert call_args["to"] == "engineer@tap.com"
    assert call_args["subject"] == "Reset Password — AI5R LTSA"
    assert "https://osa-system.com/reset-password?token=" in call_args["html"]

    # Token hash was stored, NOT raw token
    assert len(reset_repo.tokens) == 1
    token_record = list(reset_repo.tokens.values())[0]
    assert token_record["user_id"] == "user-1"
    assert len(token_record["token_hash"]) == 64  # SHA-256 hex digest
    assert token_record["used_at"] is None

    # Raw token from URL matches hash
    url = call_args["text"].split("Reset Password: ")[1].split("\n")[0]
    raw_token = url.split("token=")[1]
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    assert token_record["token_hash"] == expected_hash


def test_forgot_password_username_lookup(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    service.request_password_reset("tap_engineer", client_ip="192.168.1.2")

    assert mock_resend_client.send_email.call_count == 1
    call_args = mock_resend_client.send_email.call_args[1]
    assert call_args["to"] == "engineer@tap.com"


def test_forgot_password_nonexistent_identifier(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    # Must complete cleanly with generic behavior
    service.request_password_reset("unknown@nowhere.com", client_ip="192.168.1.3")

    assert mock_resend_client.send_email.call_count == 0
    assert len(reset_repo.tokens) == 0


def test_forgot_password_account_without_email(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    # User exists but has no email
    service.request_password_reset("no_email_user", client_ip="192.168.1.4")

    assert mock_resend_client.send_email.call_count == 0
    assert len(reset_repo.tokens) == 0


def test_forgot_password_inactive_user(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    service.request_password_reset("inactive@tap.com", client_ip="192.168.1.5")

    assert mock_resend_client.send_email.call_count == 0
    assert len(reset_repo.tokens) == 0


def test_reset_password_success(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    # 1. Request reset
    service.request_password_reset("engineer@tap.com", client_ip="192.168.1.1")
    call_args = mock_resend_client.send_email.call_args[1]
    url = call_args["text"].split("Reset Password: ")[1].split("\n")[0]
    raw_token = url.split("token=")[1]

    # 2. Reset password
    service.reset_password(raw_token, "NewSecurePassword456!", client_ip="192.168.1.1")

    # Token is marked used
    token_record = list(reset_repo.tokens.values())[0]
    assert token_record["used_at"] is not None

    # Old password no longer verifies
    user = auth_repo.find_user_by_email("engineer@tap.com")
    assert not verify_password("OldPassword123", user.password_hash)

    # New password verifies successfully
    assert verify_password("NewSecurePassword456!", user.password_hash)


def test_reset_password_reused_token(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    service.request_password_reset("engineer@tap.com")
    call_args = mock_resend_client.send_email.call_args[1]
    url = call_args["text"].split("Reset Password: ")[1].split("\n")[0]
    raw_token = url.split("token=")[1]

    # First reset succeeds
    service.reset_password(raw_token, "FirstNewPass1!")

    # Second reset with SAME token must fail
    with pytest.raises(InvalidTokenError):
        service.reset_password(raw_token, "SecondNewPass2!")


def test_reset_password_expired_token(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    # Manually insert expired token
    raw_token = "expired_raw_token"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    reset_repo.create_reset_token(
        user_id="user-1",
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    with pytest.raises(InvalidTokenError):
        service.reset_password(raw_token, "AnyPassword123")


def test_reset_password_invalid_token(auth_repo, reset_repo, mock_resend_client):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    with pytest.raises(InvalidTokenError):
        service.reset_password("totally_made_up_token", "AnyPassword123")


def test_rate_limiting_enforcement(auth_repo, reset_repo, mock_resend_client):
    limiter = PasswordResetRateLimiter(max_requests=2, window_seconds=900)
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
        rate_limiter=limiter,
    )

    # First 2 allowed
    service.request_password_reset("test1@tap.com", client_ip="10.0.0.1")
    service.request_password_reset("test2@tap.com", client_ip="10.0.0.1")

    # 3rd request from same IP is rate limited
    with pytest.raises(RateLimitExceededError):
        service.request_password_reset("test3@tap.com", client_ip="10.0.0.1")


def test_missing_resend_api_key_degradation(auth_repo, reset_repo):
    unconfigured_client = ResendClient(ResendConfig(api_key=None))
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=unconfigured_client,
    )

    # Does not crash or raise when RESEND_API_KEY is unset
    service.request_password_reset("engineer@tap.com", client_ip="192.168.1.1")
    assert len(reset_repo.tokens) == 1


def test_audit_logs_do_not_contain_secrets_or_identifiers(auth_repo, reset_repo, mock_resend_client, caplog):
    service = PasswordResetService(
        auth_repository=auth_repo,
        reset_repository=reset_repo,
        resend_client=mock_resend_client,
    )

    with caplog.at_level(logging.INFO):
        service.request_password_reset("engineer@tap.com", client_ip="192.168.1.1")

    # Check log text
    log_text = caplog.text
    assert "password_reset_requested" in log_text
    assert "engineer@tap.com" not in log_text
    assert "tap_engineer" not in log_text
    assert "token" not in log_text
    assert "re_mock" not in log_text


# --- LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -------------------------------------

import dataclasses  # noqa: E402

from API.auth_password import PasswordPolicyError  # noqa: E402


def _service(auth_repo, reset_repo, mock_resend_client):
    return PasswordResetService(auth_repository=auth_repo, reset_repository=reset_repo, resend_client=mock_resend_client)


def _issue_reset_token(service, mock_resend_client, identifier="engineer@tap.com"):
    service.request_password_reset(identifier, client_ip="192.168.1.1")
    url = mock_resend_client.send_email.call_args[1]["text"].split("Reset Password: ")[1].split("\n")[0]
    return url.split("token=")[1]


def test_reset_password_clears_forced_change_and_records_password_changed_at(auth_repo, reset_repo, mock_resend_client):
    user = auth_repo.find_user_by_email("engineer@tap.com")
    forced = dataclasses.replace(user, must_change_password=True)
    auth_repo.users["engineer@tap.com"] = forced
    auth_repo.usernames["tap_engineer"] = forced
    service = _service(auth_repo, reset_repo, mock_resend_client)
    raw_token = _issue_reset_token(service, mock_resend_client)

    service.reset_password(raw_token, "NewSecurePassword456!", client_ip="192.168.1.1")

    updated = auth_repo.find_user_by_email("engineer@tap.com")
    assert updated.must_change_password is False
    assert updated.password_changed_at is not None


@pytest.mark.parametrize("weak", ["short-pw", "             ", "tap_engineer", "Engineer@Tap.com", "x" * 129])
def test_reset_password_policy_violation_is_rejected_and_token_stays_usable(auth_repo, reset_repo, mock_resend_client, weak):
    service = _service(auth_repo, reset_repo, mock_resend_client)
    raw_token = _issue_reset_token(service, mock_resend_client)

    with pytest.raises(PasswordPolicyError):
        service.reset_password(raw_token, weak, client_ip="192.168.1.1")

    assert list(reset_repo.tokens.values())[0]["used_at"] is None
    assert verify_password("OldPassword123", auth_repo.find_user_by_email("engineer@tap.com").password_hash)

    # the same link still works with a valid password
    service.reset_password(raw_token, "NewSecurePassword456!", client_ip="192.168.1.1")
    assert verify_password("NewSecurePassword456!", auth_repo.find_user_by_email("engineer@tap.com").password_hash)


def test_reset_password_invalid_token_still_reported_as_invalid(auth_repo, reset_repo, mock_resend_client):
    service = _service(auth_repo, reset_repo, mock_resend_client)
    with pytest.raises(InvalidTokenError):
        service.reset_password("bogus-token", "NewSecurePassword456!", client_ip="192.168.1.1")


def test_reset_email_text_is_unchanged(auth_repo, reset_repo, mock_resend_client):
    service = _service(auth_repo, reset_repo, mock_resend_client)
    service.request_password_reset("engineer@tap.com", client_ip="192.168.1.1")
    kwargs = mock_resend_client.send_email.call_args[1]
    assert kwargs["subject"] == "Reset Password — AI5R LTSA"
    assert kwargs["text"].startswith(
        "AI5R LTSA Engineering\n\nA request was received to reset your password for your AI5R LTSA account.\n\nReset Password: "
    )
    assert "This password reset link is valid for 15 minutes." in kwargs["text"]


def test_send_set_password_link_emails_a_reset_token_link(auth_repo, reset_repo, mock_resend_client):
    service = _service(auth_repo, reset_repo, mock_resend_client)
    assert service.send_set_password_link("user-1") is True
    kwargs = mock_resend_client.send_email.call_args[1]
    assert kwargs["to"] == "engineer@tap.com"
    assert kwargs["subject"] == "Set your password — AI5R LTSA"
    url = kwargs["text"].split("Set Password: ")[1].split("\n")[0]
    raw_token = url.split("token=")[1]
    assert url.startswith("https://osa-system.com/reset-password?token=")
    assert len(reset_repo.tokens) == 1

    # the link is an ordinary reset token: it sets the password and clears any forced change
    service.reset_password(raw_token, "Chosen-By-User-2026", client_ip="10.0.0.1")
    user = auth_repo.find_user_by_email("engineer@tap.com")
    assert verify_password("Chosen-By-User-2026", user.password_hash)
    assert user.must_change_password is False


@pytest.mark.parametrize("user_id", ["user-2", "user-3", "missing-user"])
def test_send_set_password_link_refuses_accounts_that_cannot_receive_it(auth_repo, reset_repo, mock_resend_client, user_id):
    service = _service(auth_repo, reset_repo, mock_resend_client)
    assert service.send_set_password_link(user_id) is False
    assert mock_resend_client.send_email.call_count == 0
    assert reset_repo.tokens == {}


def test_send_set_password_link_reports_dispatch_failure(auth_repo, reset_repo, mock_resend_client):
    mock_resend_client.send_email.side_effect = RuntimeError("smtp down")
    service = _service(auth_repo, reset_repo, mock_resend_client)
    assert service.send_set_password_link("user-1") is False
