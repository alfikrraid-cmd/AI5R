"""LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- POST /api/auth/change-password,
session invalidation and the forced first-login lock, end to end through the
REAL login -> JWT -> get_current_user -> resolve_identity path.

The module-level dependencies._auth_repository (used by get_current_user) and
get_auth_repository (used by the routes) both point at one in-memory fake, so
a token issued by /api/auth/login is checked against the same users the
change-password route updates. No live Postgres needed.
"""

import dataclasses
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

import dependencies  # noqa: E402
from main import app  # noqa: E402
from dependencies import get_auth_repository, get_change_password_attempt_limiter, get_pump_gateway  # noqa: E402
from API.auth_password import hash_password, verify_password  # noqa: E402
from API.auth_service import MembershipRecord, UserRecord, issue_access_token  # noqa: E402
from API.password_reset_service import FailedPasswordAttemptLimiter  # noqa: E402

client = TestClient(app)

CURRENT = "Current-Passw0rd-2026"
NEW = "Brand-New-Passw0rd-2026"


class FakeAuthRepository:
    def __init__(self):
        self.users: dict[str, UserRecord] = {}
        self.memberships: dict[tuple[str, str], MembershipRecord] = {}
        self.audit_rows: list[dict] = []
        self.fail_next_change = False

    def add_user(self, user_id, *, username, email, password, name=None, must_change_password=False):
        self.users[user_id] = UserRecord(
            id=user_id, email=email, password_hash=hash_password(password), status="ACTIVE",
            username=username, name=name, must_change_password=must_change_password,
        )
        self.memberships[(user_id, "org-tap")] = MembershipRecord(
            organization_id="org-tap", organization_code="TAP", role="TAP_ENGINEER", status="ACTIVE",
        )

    def find_user_by_email(self, email):
        return next((u for u in self.users.values() if u.email and u.email.lower() == email.lower()), None)

    def find_user_by_username(self, username):
        return next((u for u in self.users.values() if u.username == username), None)

    def find_user_by_id(self, user_id):
        return self.users.get(user_id)

    def find_active_membership_for_user(self, user_id):
        return next((m for (uid, _), m in self.memberships.items() if uid == user_id and m.status == "ACTIVE"), None)

    def find_membership(self, user_id, organization_id):
        return self.memberships.get((user_id, organization_id))

    def change_password(self, user_id, *, expected_password_hash, new_password_hash, password_changed_at, reason):
        user = self.users.get(user_id)
        if self.fail_next_change or user is None or user.password_hash != expected_password_hash:
            return False
        self.users[user_id] = dataclasses.replace(
            user,
            password_hash=new_password_hash,
            must_change_password=False,
            password_changed_at=password_changed_at.isoformat(),
        )
        self.audit_rows.append(
            {"entity_id": user_id, "field_name": "password", "old_value": "[REDACTED]",
             "new_value": "[REDACTED]", "reason": reason}
        )
        return True


class FakePumpGateway:
    def list_pumps(self):
        return {"success": True, "message": "ok", "count": 0, "data": []}


@pytest.fixture
def repo(monkeypatch):
    app.dependency_overrides.clear()
    fake = FakeAuthRepository()
    fake.add_user("user-1", username="tap.engineer", email="eng@tap.internal", password=CURRENT, name="Tap Engineer")
    limiter = FailedPasswordAttemptLimiter()
    monkeypatch.setattr(dependencies, "_auth_repository", fake)
    app.dependency_overrides[get_auth_repository] = lambda: fake
    app.dependency_overrides[get_change_password_attempt_limiter] = lambda: limiter
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    yield fake
    app.dependency_overrides.clear()


def _login(identifier="tap.engineer", password=CURRENT):
    response = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _change(token, current=CURRENT, new=NEW):
    return client.post(
        "/api/auth/change-password", json={"current_password": current, "new_password": new}, headers=_auth(token)
    )


# --- Change password -------------------------------------------------------


def test_correct_current_password_changes_hash_and_returns_fresh_session(repo):
    token = _login()["access_token"]
    before = repo.users["user-1"].password_hash

    response = _change(token)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["must_change_password"] is False
    user = repo.users["user-1"]
    assert user.password_hash != before
    assert verify_password(NEW, user.password_hash) and not verify_password(CURRENT, user.password_hash)
    assert user.password_changed_at is not None
    assert repo.audit_rows == [
        {"entity_id": "user-1", "field_name": "password", "old_value": "[REDACTED]",
         "new_value": "[REDACTED]", "reason": "self_service_password_change"}
    ]


def test_response_never_contains_password_or_hash(repo):
    token = _login()["access_token"]
    response = _change(token)
    text = response.text
    assert CURRENT not in text and NEW not in text
    assert "scrypt$" not in text and "password_hash" not in text


def test_incorrect_current_password_is_400_not_401_and_keeps_password(repo):
    token = _login()["access_token"]
    response = _change(token, current="Wrong-Passw0rd-2026")
    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"
    assert verify_password(CURRENT, repo.users["user-1"].password_hash)
    # the session is still valid
    assert client.get("/api/auth/me", headers=_auth(token)).status_code == 200


def test_same_password_is_rejected_with_422(repo):
    token = _login()["access_token"]
    response = _change(token, new=CURRENT)
    assert response.status_code == 422
    assert "different" in response.json()["detail"]


@pytest.mark.parametrize(
    "weak",
    ["short-pw", "            ", "x" * 129, "tap.engineer", "TAP.ENGINEER", "eng@tap.internal"],
)
def test_policy_violations_are_rejected_with_422(repo, weak):
    token = _login()["access_token"]
    response = _change(token, new=weak)
    assert response.status_code == 422, weak
    assert verify_password(CURRENT, repo.users["user-1"].password_hash)


def test_unauthenticated_is_401(repo):
    response = client.post("/api/auth/change-password", json={"current_password": CURRENT, "new_password": NEW})
    assert response.status_code == 401


def test_extra_fields_are_rejected(repo):
    token = _login()["access_token"]
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": CURRENT, "new_password": NEW, "must_change_password": False},
        headers=_auth(token),
    )
    assert response.status_code == 422


def test_wrong_current_password_attempts_are_rate_limited(repo):
    token = _login()["access_token"]
    for _ in range(5):
        assert _change(token, current="Wrong-Passw0rd-2026").status_code == 400
    blocked = _change(token)  # even the right password is refused while blocked
    assert blocked.status_code == 429
    assert verify_password(CURRENT, repo.users["user-1"].password_hash)


def test_concurrent_change_is_409_and_does_not_overwrite(repo):
    token = _login()["access_token"]
    repo.fail_next_change = True
    response = _change(token)
    assert response.status_code == 409
    assert verify_password(CURRENT, repo.users["user-1"].password_hash)


# --- Session invalidation --------------------------------------------------


def test_old_token_is_rejected_and_fresh_token_accepted_after_change(repo):
    old_token = issue_access_token("user-1", "org-tap", issued_at=datetime.now(timezone.utc) - timedelta(seconds=5))
    assert client.get("/api/auth/me", headers=_auth(old_token)).status_code == 200

    fresh = _change(old_token).json()["access_token"]

    assert client.get("/api/auth/me", headers=_auth(old_token)).status_code == 401
    me = client.get("/api/auth/me", headers=_auth(fresh))
    assert me.status_code == 200
    assert me.json()["must_change_password"] is False


def test_token_issued_before_password_changed_at_is_rejected(repo):
    # Anchored in the past: PyJWT rejects an iat in the future.
    changed_at = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=10)
    repo.users["user-1"] = dataclasses.replace(repo.users["user-1"], password_changed_at=changed_at.isoformat())
    earlier = issue_access_token("user-1", "org-tap", issued_at=changed_at - timedelta(seconds=1))
    same_second = issue_access_token("user-1", "org-tap", issued_at=changed_at)
    later = issue_access_token("user-1", "org-tap", issued_at=changed_at + timedelta(seconds=1))
    assert client.get("/api/auth/me", headers=_auth(earlier)).status_code == 401
    assert client.get("/api/auth/me", headers=_auth(same_second)).status_code == 200
    assert client.get("/api/auth/me", headers=_auth(later)).status_code == 200


def test_null_password_changed_at_keeps_existing_behavior(repo):
    old = issue_access_token("user-1", "org-tap", issued_at=datetime.now(timezone.utc) - timedelta(minutes=20))
    assert repo.users["user-1"].password_changed_at is None
    assert client.get("/api/auth/me", headers=_auth(old)).status_code == 200


# --- Forced first-login lock -----------------------------------------------


def _force(repo):
    repo.users["user-1"] = dataclasses.replace(repo.users["user-1"], must_change_password=True)


def test_login_and_me_expose_must_change_password(repo):
    assert _login()["must_change_password"] is False
    _force(repo)
    body = _login()
    assert body["must_change_password"] is True
    me = client.get("/api/auth/me", headers=_auth(body["access_token"]))
    assert me.status_code == 200 and me.json()["must_change_password"] is True


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/ltsa/pumps"),
        ("GET", "/api/admin/users"),
        ("PATCH", "/api/auth/me"),
    ],
)
def test_forced_user_gets_403_password_change_required_elsewhere(repo, method, path):
    _force(repo)
    token = _login()["access_token"]
    response = client.request(method, path, headers=_auth(token), json={"email": "x@tap.internal"})
    assert response.status_code == 403
    assert response.json()["detail"] == "password_change_required"


def test_forced_user_can_change_password_and_then_use_the_api(repo):
    _force(repo)
    token = _login()["access_token"]
    assert client.get("/api/ltsa/pumps", headers=_auth(token)).status_code == 403

    response = _change(token)
    assert response.status_code == 200
    assert response.json()["must_change_password"] is False
    assert repo.users["user-1"].must_change_password is False

    fresh = response.json()["access_token"]
    assert client.get("/api/ltsa/pumps", headers=_auth(fresh)).status_code == 200


# --- Name lookup -------------------------------------------------------------


def test_name_survives_me_reload(repo):
    token = _login()["access_token"]
    me = client.get("/api/auth/me", headers=_auth(token)).json()
    assert me["name"] == "Tap Engineer"
    assert me["user"]["name"] == "Tap Engineer"
