"""MWO-LTSA-AUTH-001 -- bootstrap_admin() logic, over a fake repository
(same AuthRepositoryProtocol shape AuthRepository/AuthRepository's own
tests already use) -- no live Postgres needed. Proves: idempotency,
never resets an existing password, always grants TAP_ADMIN when missing.
"""

import sys
from pathlib import Path

INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(INGESTION_PATH))

CORE_SERVICES_PATH = Path(__file__).resolve().parents[4] / "CORE-SERVICES"
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from ltsa_bootstrap_admin import bootstrap_admin  # noqa: E402
from API.auth_password import verify_password  # noqa: E402
from API.auth_service import MembershipRecord, UserRecord  # noqa: E402


class FakeAuthRepository:
    def __init__(self, organizations=None):
        self.organizations = {"TAP": "org-tap-id"} if organizations is None else organizations
        self.users_by_email: dict[str, UserRecord] = {}
        self.memberships: dict[tuple[str, str], MembershipRecord] = {}
        self._next_id = 1

    def find_organization_by_code(self, code):
        return self.organizations.get(code)

    def find_user_by_email(self, email):
        return self.users_by_email.get(email)

    def find_membership(self, user_id, organization_id):
        return self.memberships.get((user_id, organization_id))

    def create_user(self, *, email, password_hash):
        user_id = f"user-{self._next_id}"
        self._next_id += 1
        self.users_by_email[email] = UserRecord(id=user_id, email=email, password_hash=password_hash, status="ACTIVE")
        return user_id

    def create_membership(self, *, user_id, organization_id, role):
        self.memberships[(user_id, organization_id)] = MembershipRecord(
            organization_id=organization_id, organization_code="TAP", role=role, status="ACTIVE"
        )


def _bootstrap(repo, email="admin@tap.internal", password="a-strong-password"):
    # bootstrap_admin() takes a real DatabaseRunner in production; the
    # function itself only ever calls AuthRepository(runner) internally
    # via the runner param -- for this unit test we call the underlying
    # logic against an already-constructed fake repository by monkey-
    # patching AuthRepository's constructor for the duration of the call.
    import ltsa_bootstrap_admin as module

    original = module.AuthRepository
    module.AuthRepository = lambda runner: repo
    try:
        return bootstrap_admin(runner=None, email=email, password=password)
    finally:
        module.AuthRepository = original


def test_creates_a_new_tap_admin_when_none_exists():
    repo = FakeAuthRepository()

    outcome = _bootstrap(repo)

    assert "Created new TAP_ADMIN" in outcome
    user = repo.find_user_by_email("admin@tap.internal")
    assert user is not None
    assert verify_password("a-strong-password", user.password_hash)
    membership = repo.find_membership(user.id, "org-tap-id")
    assert membership is not None
    assert membership.role == "TAP_ADMIN"


def test_running_it_again_is_idempotent_and_does_not_reset_the_password():
    repo = FakeAuthRepository()
    _bootstrap(repo, password="first-password")
    original_hash = repo.find_user_by_email("admin@tap.internal").password_hash

    outcome = _bootstrap(repo, password="a-completely-different-second-password")

    assert "no changes made" in outcome
    user = repo.find_user_by_email("admin@tap.internal")
    assert user.password_hash == original_hash  # never overwritten
    assert verify_password("first-password", user.password_hash)
    assert not verify_password("a-completely-different-second-password", user.password_hash)


def test_grants_membership_to_an_existing_user_without_touching_their_password():
    repo = FakeAuthRepository()
    user_id = repo.create_user(email="admin@tap.internal", password_hash="already-hashed-value")
    # No membership created yet -- simulates a user that exists for some
    # other reason but was never granted TAP_ADMIN.

    outcome = _bootstrap(repo)

    assert "granted TAP_ADMIN membership" in outcome
    assert "password untouched" in outcome
    user = repo.find_user_by_email("admin@tap.internal")
    assert user.password_hash == "already-hashed-value"  # untouched
    membership = repo.find_membership(user_id, "org-tap-id")
    assert membership is not None and membership.role == "TAP_ADMIN"


def test_fails_clearly_when_tap_organization_does_not_exist():
    import pytest

    repo = FakeAuthRepository(organizations={})

    with pytest.raises(RuntimeError, match="TAP"):
        _bootstrap(repo)


def test_cli_requires_environment_credentials_never_uses_a_default():
    import subprocess
    import sys as _sys

    script = Path(__file__).resolve().parents[1] / "ltsa_bootstrap_admin.py"
    result = subprocess.run(
        [_sys.executable, str(script)],
        capture_output=True,
        text=True,
        env={},
    )
    assert result.returncode == 1
    assert "AI5R_BOOTSTRAP_ADMIN_EMAIL" in result.stderr
