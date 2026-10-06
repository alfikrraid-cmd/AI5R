import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_auth_repository,
    get_password_reset_service,
)
from API.auth_service import (  # noqa: E402
    MembershipRecord,
    UserRecord,
    normalize_username,
)
from API.auth_password import hash_password  # noqa: E402
from API.password_reset_repository import FakePasswordResetRepository  # noqa: E402
from API.password_reset_service import PasswordResetRateLimiter, PasswordResetService  # noqa: E402
from API.resend_client import ResendClient, ResendConfig, ResendResult  # noqa: E402

client = TestClient(app)


class FakeAuthRepository:
    def __init__(self):
        self.users: dict[str, UserRecord] = {}
        self.usernames: dict[str, UserRecord] = {}
        self.memberships: dict[tuple[str, str], MembershipRecord] = {}

    def add_user(self, user_id, email, password, status="ACTIVE", username=None):
        user = UserRecord(
            id=user_id,
            email=email,
            password_hash=hash_password(password),
            status=status,
            username=normalize_username(username) if username else None,
        )
        if email is not None:
            self.users[email.lower()] = user
        if user.username is not None:
            self.usernames[user.username] = user
        return user

    def add_membership(self, user_id, organization_id, organization_code, role, status="ACTIVE"):
        self.memberships[(user_id, organization_id)] = MembershipRecord(
            organization_id=organization_id,
            organization_code=organization_code,
            role=role,
            status=status,
        )

    def find_user_by_email(self, email: str) -> UserRecord | None:
        return self.users.get((email or "").lower())

    def find_user_by_username(self, username: str) -> UserRecord | None:
        return self.usernames.get((username or "").lower())

    def find_user_by_id(self, user_id: str) -> UserRecord | None:
        for u in list(self.users.values()) + list(self.usernames.values()):
            if u.id == user_id:
                return u
        return None

    def find_active_membership_for_user(self, user_id: str) -> MembershipRecord | None:
        for (uid, _), m in self.memberships.items():
            if uid == user_id and m.status == "ACTIVE":
                return m
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


@pytest.fixture(autouse=True)
def _setup_app_dependencies():
    fake_auth = FakeAuthRepository()
    fake_auth.add_user("usr-1", "user@tap.com", "CurrentSecret123", username="tap_user")
    fake_auth.add_user("usr-2", None, "NoEmailPass123", username="no_email_user")
    fake_auth.add_user("usr-3", "inactive@tap.com", "InactivePass123", status="INACTIVE", username="inactive_user")
    fake_auth.add_membership("usr-1", "org-tap", "TAP", "TAP_ENGINEER")

    fake_reset_repo = FakePasswordResetRepository()

    mock_resend = ResendClient(
        ResendConfig(
            api_key="re_test_mock_secret",
            app_public_url="https://osa-system.com",
            from_email="noreply@mail.osa-system.com",
            from_name="AI5R LTSA",
        )
    )
    mock_resend.send_email = MagicMock(return_value=ResendResult(status="SUCCESS", email_id="re-123"))

    rate_limiter = PasswordResetRateLimiter(max_requests=5, window_seconds=900)

    reset_service = PasswordResetService(
        auth_repository=fake_auth,
        reset_repository=fake_reset_repo,
        resend_client=mock_resend,
        rate_limiter=rate_limiter,
    )

    app.dependency_overrides[get_auth_repository] = lambda: fake_auth
    app.dependency_overrides[get_password_reset_service] = lambda: reset_service

    yield {
        "auth_repo": fake_auth,
        "reset_repo": fake_reset_repo,
        "resend_client": mock_resend,
        "rate_limiter": rate_limiter,
    }

    app.dependency_overrides.clear()


def test_forgot_password_generic_response_for_all_inputs(_setup_app_dependencies):
    expected_message = "If the account is eligible, password reset instructions have been sent."

    # 1. Valid email
    res1 = client.post("/api/auth/forgot-password", json={"identifier": "user@tap.com"})
    assert res1.status_code == 200
    assert res1.json() == {"message": expected_message}

    # 2. Valid username
    res2 = client.post("/api/auth/forgot-password", json={"identifier": "tap_user"})
    assert res2.status_code == 200
    assert res2.json() == {"message": expected_message}

    # 3. Nonexistent user
    res3 = client.post("/api/auth/forgot-password", json={"identifier": "ghost_user"})
    assert res3.status_code == 200
    assert res3.json() == {"message": expected_message}

    # 4. User without email
    res4 = client.post("/api/auth/forgot-password", json={"identifier": "no_email_user"})
    assert res4.status_code == 200
    assert res4.json() == {"message": expected_message}

    # 5. Inactive user
    res5 = client.post("/api/auth/forgot-password", json={"identifier": "inactive_user"})
    assert res5.status_code == 200
    assert res5.json() == {"message": expected_message}


def test_forgot_password_rate_limiting(_setup_app_dependencies):
    # Send 5 requests (allowed)
    for i in range(5):
        res = client.post("/api/auth/forgot-password", json={"identifier": f"attempt{i}@tap.com"})
        assert res.status_code == 200

    # 6th request is rate limited
    blocked_res = client.post("/api/auth/forgot-password", json={"identifier": "attempt6@tap.com"})
    assert blocked_res.status_code == 429
    assert "Too many password reset requests" in blocked_res.json()["detail"]


def test_full_reset_password_flow_and_login_acceptance(_setup_app_dependencies):
    resend_client = _setup_app_dependencies["resend_client"]

    # 1. Request forgot-password
    res = client.post("/api/auth/forgot-password", json={"identifier": "user@tap.com"})
    assert res.status_code == 200

    # Extract raw token from mock email call
    assert resend_client.send_email.call_count == 1
    call_args = resend_client.send_email.call_args[1]
    text_content = call_args["text"]
    url = text_content.split("Reset Password: ")[1].split("\n")[0]
    raw_token = url.split("token=")[1]

    # 2. Reset password
    new_password = "BrandNewSuperSecret2026!"
    reset_res = client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": new_password},
    )
    assert reset_res.status_code == 200
    assert "Password has been successfully reset" in reset_res.json()["message"]

    # 3. Old password is now rejected
    old_login = client.post("/api/auth/login", json={"identifier": "tap_user", "password": "CurrentSecret123"})
    assert old_login.status_code == 401

    # 4. New password is accepted
    new_login = client.post("/api/auth/login", json={"identifier": "tap_user", "password": new_password})
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_reset_password_token_reuse_rejected(_setup_app_dependencies):
    resend_client = _setup_app_dependencies["resend_client"]

    client.post("/api/auth/forgot-password", json={"identifier": "user@tap.com"})
    url = resend_client.send_email.call_args[1]["text"].split("Reset Password: ")[1].split("\n")[0]
    raw_token = url.split("token=")[1]

    # First reset
    first_res = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "NewPassword1!"})
    assert first_res.status_code == 200

    # Second reset with SAME token
    second_res = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "NewPassword2!"})
    assert second_res.status_code == 400
    assert "Invalid or expired" in second_res.json()["detail"]


def test_reset_password_invalid_or_expired_token(_setup_app_dependencies):
    # Nonexistent token
    invalid_res = client.post("/api/auth/reset-password", json={"token": "bogus_token_value", "new_password": "NewPassword1!"})
    assert invalid_res.status_code == 400
    assert "Invalid or expired" in invalid_res.json()["detail"]


def test_normal_login_regression(_setup_app_dependencies):
    login_res = client.post("/api/auth/login", json={"identifier": "tap_user", "password": "CurrentSecret123"})
    assert login_res.status_code == 200
    body = login_res.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "tap_user"
    assert "password_hash" not in str(body)
