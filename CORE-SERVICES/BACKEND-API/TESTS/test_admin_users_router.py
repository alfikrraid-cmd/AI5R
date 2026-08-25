"""MWO-LTSA-AUTH-003A-FINAL -- Admin Users API router tests."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_auth_repository, get_current_user  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity, normalize_username  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakeMembership:
    def __init__(self, organization_id, organization_code, role, status="ACTIVE"):
        self.organization_id = organization_id
        self.organization_code = organization_code
        self.role = role
        self.status = status


class FakeAuthRepository:
    def __init__(self, *, memberships=None, active_superuser_count=1, superuser_ids=None, organizations=None):
        # memberships: {(user_id, organization_id): FakeMembership}
        self.memberships = memberships or {}
        self._active_superuser_count = active_superuser_count
        self._superuser_ids = superuser_ids or set()
        self.created_users = []
        self.existing_usernames = set()
        self.existing_emails = set()
        self.organizations = set(organizations or {"org-tap"})
        self.created_memberships = []
        self.status_updates = []
        self.role_updates = []
        self.password_updates = []

    def list_users(self):
        return [
            {
                "id": "u-1", "username": "tapeng", "email": "u1@tap.internal", "user_status": "ACTIVE",
                "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
                "created_by": None, "updated_by": None,
                "organization_id": "org-tap", "organization_code": "TAP", "organization_name": "TAP",
                "role": "TAP_ENGINEER", "membership_status": "ACTIVE",
            }
        ]

    def find_user_by_username(self, username):
        return {"username": username} if normalize_username(username) in self.existing_usernames else None

    def find_user_by_email(self, email):
        return {"email": email} if email.strip().lower() in self.existing_emails else None

    def find_organization_by_id(self, organization_id):
        return organization_id if organization_id in self.organizations else None

    def create_user(self, *, username, email, password_hash, created_by=None):
        self.created_users.append({"username": username, "email": email, "password_hash": password_hash, "created_by": created_by})
        return "new-user-id"

    def create_membership(self, *, user_id, organization_id, role, created_by=None):
        self.created_memberships.append(
            {"user_id": user_id, "organization_id": organization_id, "role": role, "created_by": created_by}
        )

    def create_user_with_membership(self, *, username, email, password_hash, organization_id, role, created_by=None):
        user_id = self.create_user(username=username, email=email, password_hash=password_hash, created_by=created_by)
        self.create_membership(user_id=user_id, organization_id=organization_id, role=role, created_by=created_by)
        return user_id

    def find_active_membership_for_user(self, user_id):
        for (uid, _org), membership in self.memberships.items():
            if uid == user_id:
                return membership
        return None

    def find_membership(self, user_id, organization_id):
        return self.memberships.get((user_id, organization_id))

    def is_active_superuser(self, user_id):
        return user_id in self._superuser_ids

    def count_active_superusers(self):
        return self._active_superuser_count

    def update_user_status(self, user_id, status, *, updated_by):
        self.status_updates.append({"user_id": user_id, "status": status, "updated_by": updated_by})

    def update_membership_role(self, user_id, organization_id, role, *, updated_by):
        self.role_updates.append(
            {"user_id": user_id, "organization_id": organization_id, "role": role, "updated_by": updated_by}
        )

    def update_password_hash(self, user_id, password_hash, *, updated_by):
        self.password_updates.append({"user_id": user_id, "password_hash": password_hash, "updated_by": updated_by})


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


class MembershipFailureRepository(FakeAuthRepository):
    def create_user_with_membership(self, *, username, email, password_hash, organization_id, role, created_by=None):
        self.user_insert_attempted = True
        raise RuntimeError("membership insert failed")


def _override(role="SUPERUSER", repo=None):
    app.dependency_overrides[get_current_user] = lambda: _identity(role)
    app.dependency_overrides[get_auth_repository] = lambda: (repo or FakeAuthRepository())


class TestPermissionGate:
    def test_tap_engineer_without_admin_users_gets_403(self):
        _override(role="TAP_ENGINEER")
        response = client.get("/api/admin/users")
        assert response.status_code == 403

    def test_john_crane_engineer_without_admin_users_gets_403(self):
        _override(role="JOHN_CRANE_ENGINEER")
        response = client.get("/api/admin/users")
        assert response.status_code == 403

    def test_pertamina_engineer_without_admin_users_gets_403(self):
        _override(role="PERTAMINA_ENGINEER")
        response = client.get("/api/admin/users")
        assert response.status_code == 403

    def test_tap_admin_has_admin_users_and_can_list(self):
        _override(role="TAP_ADMIN")
        response = client.get("/api/admin/users")
        assert response.status_code == 200


class TestListUsers:
    def test_list_never_exposes_password_hash(self):
        _override(role="SUPERUSER")
        response = client.get("/api/admin/users")
        assert response.status_code == 200
        body = response.json()
        for user in body["users"]:
            assert "password_hash" not in user
            assert "password" not in user

    def test_tap_admin_list_marks_unmanageable_rows_without_failing_page(self):
        class MixedRoleRepo(FakeAuthRepository):
            def list_users(self):
                rows = super().list_users()
                rows.append({**rows[0], "id": "admin-1", "role": "TAP_ADMIN"})
                rows.append({**rows[0], "id": "su-1", "role": "SUPERUSER"})
                return rows

        _override(role="TAP_ADMIN", repo=MixedRoleRepo())
        response = client.get("/api/admin/users")
        assert response.status_code == 200
        users = response.json()["users"]
        assert [user["can_manage"] for user in users] == [True, False, False]

class TestCreateUser:
    def test_superuser_can_create_any_role(self):
        repo = FakeAuthRepository()
        _override(role="SUPERUSER", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "newuser", "email": "new@tap.internal", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
        )
        assert response.status_code == 200
        assert repo.created_users[0]["created_by"] == "actor-1"
        assert "password" not in response.json()
        assert "password_hash" not in response.json()

    def test_created_password_is_hashed_never_stored_plaintext(self):
        repo = FakeAuthRepository()
        _override(role="SUPERUSER", repo=repo)
        client.post(
            "/api/admin/users",
            json={"username": "newuser", "email": "new@tap.internal", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
        )
        assert repo.created_users[0]["password_hash"] != "s3cret-pw"

    def test_tap_admin_can_create_tap_engineer(self):
        repo = FakeAuthRepository()
        _override(role="TAP_ADMIN", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "newuser", "email": "new@tap.internal", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
        )
        assert response.status_code == 200

    def test_tap_admin_cannot_create_superuser(self):
        repo = FakeAuthRepository()
        _override(role="TAP_ADMIN", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "newadmin", "email": "new@tap.internal", "password": "s3cret-pw", "organization_id": "org-tap", "role": "SUPERUSER"},
        )
        assert response.status_code == 403
        assert repo.created_users == []

    def test_tap_admin_can_create_john_crane_engineer(self):
        repo = FakeAuthRepository()
        _override(role="TAP_ADMIN", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "jcuser", "email": "jc@johncrane.internal", "password": "s3cret-pw", "organization_id": "org-tap", "role": "JOHN_CRANE_ENGINEER"},
        )
        assert response.status_code == 200

    def test_tap_admin_cannot_create_tap_admin(self):
        repo = FakeAuthRepository()
        _override(role="TAP_ADMIN", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "newadmin", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ADMIN"},
        )
        assert response.status_code == 403
        assert repo.created_users == []

    def test_tap_admin_cannot_create_outside_own_organization(self):
        repo = FakeAuthRepository(organizations={"org-tap", "org-other"})
        _override(role="TAP_ADMIN", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "newuser", "password": "s3cret-pw", "organization_id": "org-other", "role": "TAP_ENGINEER"},
        )
        assert response.status_code == 403
        assert repo.created_users == []

    def test_create_user_success_persists_user_and_membership(self):
        repo = FakeAuthRepository()
        _override(role="SUPERUSER", repo=repo)
        before_users = len(repo.created_users)
        before_memberships = len(repo.created_memberships)

        response = client.post(
            "/api/admin/users",
            json={"username": "newuser", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
        )

        assert response.status_code == 200
        assert len(repo.created_users) == before_users + 1
        assert len(repo.created_memberships) == before_memberships + 1

    def test_membership_failure_does_not_leave_partial_user(self):
        repo = MembershipFailureRepository()
        _override(role="SUPERUSER", repo=repo)
        before_users = len(repo.created_users)
        before_memberships = len(repo.created_memberships)

        response = client.post(
            "/api/admin/users",
            json={"username": "newuser", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
        )

        assert response.status_code == 500
        assert repo.user_insert_attempted is True
        assert len(repo.created_users) == before_users
        assert len(repo.created_memberships) == before_memberships
        assert repo.find_user_by_username("newuser") is None

    def test_invalid_organization_does_not_create_user(self):
        repo = FakeAuthRepository()
        _override(role="SUPERUSER", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "newuser", "password": "s3cret-pw", "organization_id": "org-missing", "role": "TAP_ENGINEER"},
        )
        assert response.status_code == 404
        assert repo.created_users == []
        assert repo.created_memberships == []

    def test_invalid_role_does_not_create_user(self):
        repo = FakeAuthRepository()
        _override(role="SUPERUSER", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "newuser", "password": "s3cret-pw", "organization_id": "org-tap", "role": "NOT_A_ROLE"},
        )
        assert response.status_code == 422
        assert repo.created_users == []
        assert repo.created_memberships == []

    def test_duplicate_email_does_not_create_partial_user(self):
        repo = FakeAuthRepository()
        repo.existing_emails.add("new@tap.internal")
        _override(role="SUPERUSER", repo=repo)
        response = client.post(
            "/api/admin/users",
            json={"username": "newuser", "email": "NEW@TAP.INTERNAL", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
        )
        assert response.status_code == 409
        assert repo.created_users == []
        assert repo.created_memberships == []

class TestUpdateUserStatus:
    def test_disabling_an_ordinary_user_succeeds(self):
        repo = FakeAuthRepository(memberships={("u-1", "org-tap"): FakeMembership("org-tap", "TAP", "TAP_ENGINEER")})
        _override(role="TAP_ADMIN", repo=repo)
        response = client.patch("/api/admin/users/u-1/status", json={"status": "DISABLED"})
        assert response.status_code == 200
        assert repo.status_updates[0]["updated_by"] == "actor-1"

    def test_disabling_the_last_active_superuser_is_refused(self):
        repo = FakeAuthRepository(
            memberships={("su-1", "org-tap"): FakeMembership("org-tap", "TAP", "SUPERUSER")},
            active_superuser_count=1,
            superuser_ids={"su-1"},
        )
        _override(role="SUPERUSER", repo=repo)
        response = client.patch("/api/admin/users/su-1/status", json={"status": "DISABLED"})
        assert response.status_code == 409
        assert repo.status_updates == []

    def test_disabling_one_of_two_active_superusers_succeeds(self):
        repo = FakeAuthRepository(
            memberships={("su-2", "org-tap"): FakeMembership("org-tap", "TAP", "SUPERUSER")},
            active_superuser_count=2,
            superuser_ids={"su-2"},
        )
        _override(role="SUPERUSER", repo=repo)
        response = client.patch("/api/admin/users/su-2/status", json={"status": "DISABLED"})
        assert response.status_code == 200

    def test_tap_admin_cannot_disable_a_tap_admin_account(self):
        repo = FakeAuthRepository(
            memberships={("admin-1", "org-tap"): FakeMembership("org-tap", "TAP", "TAP_ADMIN")},
        )
        _override(role="TAP_ADMIN", repo=repo)
        response = client.patch("/api/admin/users/admin-1/status", json={"status": "DISABLED"})
        assert response.status_code == 403
        assert repo.status_updates == []

    def test_tap_admin_cannot_disable_a_superuser_account(self):
        repo = FakeAuthRepository(
            memberships={("su-1", "org-tap"): FakeMembership("org-tap", "TAP", "SUPERUSER")},
            active_superuser_count=2,
            superuser_ids={"su-1"},
        )
        _override(role="TAP_ADMIN", repo=repo)
        response = client.patch("/api/admin/users/su-1/status", json={"status": "DISABLED"})
        assert response.status_code == 403

    def test_enabling_a_disabled_user_never_triggers_last_superuser_guard(self):
        repo = FakeAuthRepository(
            memberships={("su-1", "org-tap"): FakeMembership("org-tap", "TAP", "SUPERUSER", status="DISABLED")},
            active_superuser_count=0,
            superuser_ids=set(),
        )
        _override(role="SUPERUSER", repo=repo)
        response = client.patch("/api/admin/users/su-1/status", json={"status": "ACTIVE"})
        assert response.status_code == 200


class TestUpdateMembershipRole:
    def test_superuser_can_promote_tap_engineer_to_tap_admin(self):
        repo = FakeAuthRepository(memberships={("u-1", "org-tap"): FakeMembership("org-tap", "TAP", "TAP_ENGINEER")})
        _override(role="SUPERUSER", repo=repo)
        response = client.patch("/api/admin/users/u-1/role", json={"organization_id": "org-tap", "role": "TAP_ADMIN"})
        assert response.status_code == 200

    def test_tap_admin_cannot_promote_anyone_to_superuser(self):
        repo = FakeAuthRepository(memberships={("u-1", "org-tap"): FakeMembership("org-tap", "TAP", "TAP_ENGINEER")})
        _override(role="TAP_ADMIN", repo=repo)
        response = client.patch("/api/admin/users/u-1/role", json={"organization_id": "org-tap", "role": "SUPERUSER"})
        assert response.status_code == 403
        assert repo.role_updates == []

    def test_demoting_the_last_superuser_is_refused(self):
        repo = FakeAuthRepository(
            memberships={("su-1", "org-tap"): FakeMembership("org-tap", "TAP", "SUPERUSER")},
            active_superuser_count=1,
            superuser_ids={"su-1"},
        )
        _override(role="SUPERUSER", repo=repo)
        response = client.patch("/api/admin/users/su-1/role", json={"organization_id": "org-tap", "role": "TAP_ADMIN"})
        assert response.status_code == 409
        assert repo.role_updates == []

    def test_unknown_membership_returns_404(self):
        repo = FakeAuthRepository()
        _override(role="SUPERUSER", repo=repo)
        response = client.patch("/api/admin/users/ghost/role", json={"organization_id": "org-tap", "role": "TAP_ADMIN"})
        assert response.status_code == 404


class TestResetPassword:
    def test_reset_never_echoes_the_new_password_or_its_hash(self):
        repo = FakeAuthRepository(memberships={("u-1", "org-tap"): FakeMembership("org-tap", "TAP", "TAP_ENGINEER")})
        _override(role="TAP_ADMIN", repo=repo)
        response = client.post("/api/admin/users/u-1/password-reset", json={"new_password": "brand-new-pw"})
        assert response.status_code == 200
        body_text = response.text
        assert "brand-new-pw" not in body_text
        assert repo.password_updates[0]["password_hash"] != "brand-new-pw"

    def test_tap_admin_cannot_reset_a_superuser_password(self):
        repo = FakeAuthRepository(memberships={("su-1", "org-tap"): FakeMembership("org-tap", "TAP", "SUPERUSER")})
        _override(role="TAP_ADMIN", repo=repo)
        response = client.post("/api/admin/users/su-1/password-reset", json={"new_password": "brand-new-pw"})
        assert response.status_code == 403
        assert repo.password_updates == []

# --- MWO-AUTH-USERNAME-001: username create contract ---------------------


def test_create_user_username_only_email_null():
    repo = FakeAuthRepository()
    _override(role="SUPERUSER", repo=repo)

    response = client.post(
        "/api/admin/users",
        json={"username": " Ravi ", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
    )

    assert response.status_code == 200
    assert repo.created_users[0]["username"] == "ravi"
    assert repo.created_users[0]["email"] is None
    assert response.json()["email"] is None


def test_create_user_username_and_email():
    repo = FakeAuthRepository()
    _override(role="SUPERUSER", repo=repo)

    response = client.post(
        "/api/admin/users",
        json={"username": "ravi", "email": "RAVI@TAP.INTERNAL", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
    )

    assert response.status_code == 200
    assert repo.created_users[0]["username"] == "ravi"
    assert repo.created_users[0]["email"] == "ravi@tap.internal"


def test_create_user_duplicate_username_rejected():
    repo = FakeAuthRepository()
    repo.existing_usernames.add("ravi")
    _override(role="SUPERUSER", repo=repo)

    response = client.post(
        "/api/admin/users",
        json={"username": "ravi", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
    )

    assert response.status_code == 409
    assert repo.created_users == []
    assert repo.created_memberships == []


def test_create_user_case_collision_rejected():
    repo = FakeAuthRepository()
    repo.existing_usernames.add("ravi")
    _override(role="SUPERUSER", repo=repo)

    response = client.post(
        "/api/admin/users",
        json={"username": " RAVI ", "password": "s3cret-pw", "organization_id": "org-tap", "role": "TAP_ENGINEER"},
    )

    assert response.status_code == 409
    assert repo.created_users == []
    assert repo.created_memberships == []
