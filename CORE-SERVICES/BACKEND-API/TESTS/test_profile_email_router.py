"""Self-service profile email security suite for PATCH /api/auth/me (R2B).

Proves, against the real FastAPI app and the real auth router:
1. Authentication: an anonymous request is rejected (401) before any update.
2. Own record only: the update is keyed on the authenticated identity; another
   user's record is never touched, and a supplied user_id is rejected.
3. Field lockdown: role, organization, permissions, username, name and
   data_scope_type/value cannot be self-modified (422, request model forbids
   extra fields), with or without an accompanying email.
4. Validation: blank, whitespace-only and malformed emails are rejected (422);
   an email owned by another user is rejected (409); the stored value is
   trimmed and lower-cased.
5. Idempotency: re-submitting the current email writes nothing.
6. Audit: the change history entry redacts both old and new email.
7. No leakage: the response carries no password hash, token or secret.

Only the repository-backed identity lookup, the auth repository and the
change-history repository are swapped for in-memory fakes -- no live
Postgres needed.
"""

import dataclasses
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
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity, UserRecord  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer overridden"}
OWN_EMAIL = "me@tap.internal"
OTHER_EMAIL = "other@tap.internal"


class FakeAuthRepository:
    def __init__(self):
        self.users: dict[str, UserRecord] = {}
        self.update_calls: list[tuple[str, str]] = []

    def add_user(self, user_id, email, username):
        self.users[user_id] = UserRecord(
            id=user_id, email=email, password_hash="hash-must-never-leak", status="ACTIVE", username=username
        )

    def find_user_by_email(self, email):
        return next((u for u in self.users.values() if u.email and u.email.lower() == email.lower()), None)

    def find_user_by_id(self, user_id):
        return self.users.get(user_id)

    def update_user_email(self, user_id, email, *, updated_by=None):
        self.update_calls.append((user_id, email))
        self.users[user_id] = dataclasses.replace(self.users[user_id], email=email.lower())


class FakeChangeHistory:
    def __init__(self):
        self.rows: list[dict] = []

    def append(self, **kwargs):
        self.rows.append(kwargs)


@pytest.fixture
def env():
    app.dependency_overrides.clear()
    repo = FakeAuthRepository()
    repo.add_user("user-me", OWN_EMAIL, "me.user")
    repo.add_user("user-other", OTHER_EMAIL, "other.user")
    history = FakeChangeHistory()
    identity = AuthenticatedIdentity(
        user_id="user-me", email=OWN_EMAIL, organization_id="org-tap", organization_code="TAP",
        role="TAP_ENGINEER", permissions=ROLE_PERMISSIONS["TAP_ENGINEER"],
        username="me.user", name="Me User",
    )
    app.dependency_overrides[get_auth_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: identity
    app.dependency_overrides[get_record_change_history_repository] = lambda: history
    yield repo, history
    app.dependency_overrides.clear()


def _unchanged(repo):
    assert repo.update_calls == []
    assert repo.find_user_by_id("user-me").email == OWN_EMAIL
    assert repo.find_user_by_id("user-other").email == OTHER_EMAIL


def test_authentication_required():
    app.dependency_overrides.clear()
    response = client.patch("/api/auth/me", json={"email": "new@tap.internal"})
    assert response.status_code == 401


def test_updates_only_own_email_and_normalizes(env):
    repo, _ = env
    response = client.patch("/api/auth/me", json={"email": "  New.Me@TAP.Internal  "}, headers=AUTH)
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "new.me@tap.internal"
    assert repo.update_calls == [("user-me", "new.me@tap.internal")]
    assert repo.find_user_by_id("user-other").email == OTHER_EMAIL


@pytest.mark.parametrize(
    "field,value",
    [
        ("user_id", "user-other"),
        ("id", "user-other"),
        ("username", "root.user"),
        ("name", "Someone Else"),
        ("organization", "PERTAMINA"),
        ("organization_id", "org-pertamina"),
        ("role", "SUPERUSER"),
        ("permissions", ["admin.users"]),
        ("data_scope_type", "ALL"),
        ("data_scope_value", "HOC"),
    ],
)
def test_cannot_self_modify_other_fields(env, field, value):
    repo, history = env
    response = client.patch("/api/auth/me", json={"email": "new@tap.internal", field: value}, headers=AUTH)
    assert response.status_code == 422, (field, response.status_code, response.text)
    _unchanged(repo)
    assert history.rows == []


@pytest.mark.parametrize("field,value", [("role", "SUPERUSER"), ("data_scope_type", "ALL")])
def test_forbidden_field_without_email_is_rejected(env, field, value):
    repo, _ = env
    response = client.patch("/api/auth/me", json={field: value}, headers=AUTH)
    assert response.status_code == 422
    _unchanged(repo)


def test_duplicate_email_is_rejected_case_insensitively(env):
    repo, history = env
    response = client.patch("/api/auth/me", json={"email": " OTHER@tap.internal "}, headers=AUTH)
    assert response.status_code == 409
    _unchanged(repo)
    assert history.rows == []


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_blank_or_whitespace_email_is_rejected(env, blank):
    repo, _ = env
    response = client.patch("/api/auth/me", json={"email": blank}, headers=AUTH)
    assert response.status_code == 422
    _unchanged(repo)


@pytest.mark.parametrize(
    "malformed",
    ["noatsign", "@tap.internal", "me@", "me@tap", "a@b@c.d", "me@.tap", "me@tap."],
)
def test_malformed_email_is_rejected(env, malformed):
    repo, _ = env
    response = client.patch("/api/auth/me", json={"email": malformed}, headers=AUTH)
    assert response.status_code == 422, malformed
    _unchanged(repo)


def test_same_email_is_idempotent(env):
    repo, history = env
    response = client.patch("/api/auth/me", json={"email": " ME@TAP.INTERNAL "}, headers=AUTH)
    assert response.status_code == 200
    assert response.json()["email"] == OWN_EMAIL
    _unchanged(repo)
    assert history.rows == []


def test_audit_entry_redacts_email(env):
    _, history = env
    client.patch("/api/auth/me", json={"email": "new.me@tap.internal"}, headers=AUTH)
    assert len(history.rows) == 1
    row = history.rows[0]
    assert row["entity_type"] == "user" and row["entity_id"] == "user-me" and row["field_name"] == "email"
    assert row["old_value"] == "[REDACTED]" and row["new_value"] == "[REDACTED]"
    assert "tap.internal" not in repr(row)


def test_response_leaks_no_password_token_or_secret(env):
    response = client.patch("/api/auth/me", json={"email": "new.me@tap.internal"}, headers=AUTH)
    body = response.json()
    # The only password-related field is the boolean first-login flag.
    password_keys = [key for key in body if "password" in key.lower()]
    assert password_keys == ["must_change_password"]
    assert isinstance(body["must_change_password"], bool)
    text = response.text.lower()
    for marker in ("password_hash", "hash-must-never-leak", "scrypt$", "token", "secret"):
        assert marker not in text, marker
