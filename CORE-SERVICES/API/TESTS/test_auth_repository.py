"""MWO-LTSA-AUTH-001A -- regression coverage for a real bug Task 5's
real-Postgres verification caught: create_user() originally passed an
INSERT...RETURNING statement through _json_query(), which wraps its
argument as `SELECT ... FROM (<sql>) t` -- valid only for a plain SELECT,
not a bare INSERT (Postgres syntax error). Fixed to build the same
WITH-CTE shape import_session_repository.py's claim_for_execution()
already established for this exact situation. No prior test caught this
because every earlier AuthRepository consumer test used a duck-typed
fake (AuthRepositoryProtocol), which never executes real SQL -- this
file instead inspects the actual SQL string create_user() builds.
"""

import json
import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.auth_repository import AuthRepository  # noqa: E402


class FakeRunner:
    """Captures the exact SQL AuthRepository builds, without a real
    connection -- proves SQL SHAPE, not database behavior (Task 5's
    real-Postgres run separately proves the shape actually executes)."""

    def __init__(self, scalar_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.script_calls: list[str] = []
        self.scalar_response = scalar_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.scalar_response

    def execute_script(self, sql: str) -> None:
        self.script_calls.append(sql)


def test_create_user_never_wraps_a_bare_insert_in_a_select_from_subquery():
    # The exact bug: `SELECT ... FROM (INSERT INTO ...) t` is invalid
    # PostgreSQL syntax. This must never reappear.
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-1"}]))
    repo = AuthRepository(runner)

    repo.create_user(username="newuser", email="new@tap.internal", password_hash="scrypt$...")

    sql = runner.scalar_calls[0]
    assert "FROM (INSERT" not in sql


def test_create_user_uses_a_data_modifying_cte_shape():
    # Same fix shape as import_session_repository.py's
    # claim_for_execution(): WITH <alias> AS (INSERT ... RETURNING ...)
    # SELECT ... FROM <alias>.
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-1"}]))
    repo = AuthRepository(runner)

    repo.create_user(username="newuser", email="new@tap.internal", password_hash="scrypt$...")

    sql = runner.scalar_calls[0]
    assert sql.strip().upper().startswith("WITH")
    assert "INSERT INTO users" in sql
    assert "RETURNING id" in sql


def test_create_user_returns_the_id_from_the_real_response_shape():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "real-uuid-value"}]))
    repo = AuthRepository(runner)

    user_id = repo.create_user(username="newuser", email="new@tap.internal", password_hash="scrypt$...")

    assert user_id == "real-uuid-value"


def test_create_membership_uses_execute_script_not_json_query():
    # Fire-and-forget INSERT ... ON CONFLICT DO NOTHING has no return
    # value to parse -- execute_script (raw execution), never
    # _json_query's SELECT-wrapping, which create_membership never needed
    # in the first place (only create_user had this bug).
    runner = FakeRunner()
    repo = AuthRepository(runner)

    repo.create_membership(user_id="u-1", organization_id="org-1", role="TAP_ADMIN")

    assert len(runner.script_calls) == 1
    assert runner.scalar_calls == []
    assert "INSERT INTO organization_memberships" in runner.script_calls[0]
    assert "ON CONFLICT" in runner.script_calls[0]


def test_find_organization_by_code_uses_a_plain_select_via_json_query():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "org-1"}]))
    repo = AuthRepository(runner)

    organization_id = repo.find_organization_by_code("TAP")

    assert organization_id == "org-1"
    assert "SELECT" in runner.scalar_calls[0]
    assert "FROM (SELECT" in runner.scalar_calls[0] or "FROM (" in runner.scalar_calls[0]


# --- MWO-LTSA-AUTH-003A-FINAL -- User Administration coverage --------------


def test_create_user_defaults_created_by_and_updated_by_to_null_for_the_bootstrap_case():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-1"}]))
    repo = AuthRepository(runner)

    repo.create_user(username="newuser", email="new@tap.internal", password_hash="scrypt$...")

    sql = runner.scalar_calls[0]
    assert "NULL, NULL" in sql or "NULL,NULL" in sql.replace(" ", "")


def test_create_user_records_created_by_when_an_authenticated_actor_exists():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-2"}]))
    repo = AuthRepository(runner)

    repo.create_user(username="newuser", email="new@tap.internal", password_hash="scrypt$...", created_by="actor-uuid")

    sql = runner.scalar_calls[0]
    assert "'actor-uuid'" in sql


def test_create_user_never_logs_or_returns_a_plaintext_password():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-3"}]))
    repo = AuthRepository(runner)

    user_id = repo.create_user(username="newuser", email="new@tap.internal", password_hash="scrypt$n$r$p$salt$hash", created_by=None)

    # Only the already-hashed value ever appears -- this function never
    # receives a plaintext password at all (the caller hashes first).
    assert user_id == "u-3"
    assert "scrypt$n$r$p$salt$hash" in runner.scalar_calls[0]


def test_update_user_status_uses_execute_script_and_sets_updated_by():
    runner = FakeRunner()
    repo = AuthRepository(runner)

    repo.update_user_status("u-1", "DISABLED", updated_by="actor-uuid")

    assert len(runner.script_calls) == 1
    sql = runner.script_calls[0]
    assert "UPDATE users" in sql
    assert "'DISABLED'" in sql
    assert "'actor-uuid'" in sql
    assert "created_by" not in sql  # never overwrites the creator


def test_update_membership_role_scopes_to_user_and_organization():
    runner = FakeRunner()
    repo = AuthRepository(runner)

    repo.update_membership_role("u-1", "org-1", "TAP_ENGINEER", updated_by="actor-uuid")

    sql = runner.script_calls[0]
    assert "UPDATE organization_memberships" in sql
    assert "'TAP_ENGINEER'" in sql
    assert "user_id = 'u-1'" in sql
    assert "organization_id = 'org-1'" in sql


def test_update_password_hash_never_receives_or_logs_plaintext():
    runner = FakeRunner()
    repo = AuthRepository(runner)

    repo.update_password_hash("u-1", "scrypt$n$r$p$newsalt$newhash", updated_by="actor-uuid")

    sql = runner.script_calls[0]
    assert "scrypt$n$r$p$newsalt$newhash" in sql
    assert "UPDATE users" in sql


def test_count_active_superusers_uses_a_plain_select_via_json_query():
    runner = FakeRunner(scalar_response=json.dumps([{"n": 2}]))
    repo = AuthRepository(runner)

    count = repo.count_active_superusers()

    assert count == 2
    assert "SUPERUSER" in runner.scalar_calls[0]


def test_is_active_superuser_scopes_by_user_id():
    runner = FakeRunner(scalar_response=json.dumps([{"n": 1}]))
    repo = AuthRepository(runner)

    assert repo.is_active_superuser("u-1") is True
    assert "u-1" in runner.scalar_calls[0]


def test_list_users_left_joins_membership_so_a_membershipless_user_still_appears():
    runner = FakeRunner(scalar_response=json.dumps([]))
    repo = AuthRepository(runner)

    repo.list_users()

    sql = runner.scalar_calls[0]
    assert "LEFT JOIN organization_memberships" in sql
    assert "LEFT JOIN organizations" in sql

# --- MWO-AUTH-USERNAME-001: username SQL shape ---------------------------


def test_create_user_writes_normalized_username_and_nullable_email():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-4"}]))
    repo = AuthRepository(runner)

    repo.create_user(username=" Ravi ", email=None, password_hash="scrypt$...", created_by="actor-uuid")

    sql = runner.scalar_calls[0]
    assert "INSERT INTO users (username, email, password_hash" in sql
    assert "'ravi'" in sql
    assert "NULL" in sql


def test_find_user_by_username_uses_normalized_username_lookup():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-1", "username": "ravi", "email": None, "password_hash": "scrypt$...", "status": "ACTIVE"}]))
    repo = AuthRepository(runner)

    user = repo.find_user_by_username(" RAVI ")

    assert user.username == "ravi"
    assert user.email is None
    assert "WHERE username = 'ravi'" in runner.scalar_calls[0]


def test_list_users_selects_username_for_admin_user_management():
    runner = FakeRunner(scalar_response=json.dumps([]))
    repo = AuthRepository(runner)

    repo.list_users()

    assert "u.username" in runner.scalar_calls[0]
# --- MWO-AUTH-USERNAME-003: atomic Admin Users create -------------------


def test_create_user_with_membership_is_one_atomic_statement():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-5"}]))
    repo = AuthRepository(runner)

    repo.create_user_with_membership(
        username="newuser",
        email=None,
        password_hash="scrypt$...",
        organization_id="org-tap",
        role="TAP_ENGINEER",
        created_by="actor-uuid",
    )

    assert len(runner.scalar_calls) == 1
    assert runner.script_calls == []
    sql = runner.scalar_calls[0]
    assert "WITH ins_user AS" in sql
    assert "INSERT INTO users" in sql
    assert "ins_membership AS" in sql
    assert "INSERT INTO organization_memberships" in sql
    assert "ON CONFLICT" not in sql


def test_create_user_with_membership_returns_new_user_id():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "real-uuid-value"}]))
    repo = AuthRepository(runner)

    user_id = repo.create_user_with_membership(
        username="newuser",
        email="new@tap.internal",
        password_hash="scrypt$...",
        organization_id="org-tap",
        role="TAP_ENGINEER",
    )

    assert user_id == "real-uuid-value"


def test_find_organization_by_id_uses_plain_select():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "org-tap"}]))
    repo = AuthRepository(runner)

    organization_id = repo.find_organization_by_id("org-tap")

    assert organization_id == "org-tap"
    assert "FROM organizations" in runner.scalar_calls[0]
    assert "WHERE id = 'org-tap'" in runner.scalar_calls[0]
