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

    repo.create_user(email="new@tap.internal", password_hash="scrypt$...")

    sql = runner.scalar_calls[0]
    assert "FROM (INSERT" not in sql


def test_create_user_uses_a_data_modifying_cte_shape():
    # Same fix shape as import_session_repository.py's
    # claim_for_execution(): WITH <alias> AS (INSERT ... RETURNING ...)
    # SELECT ... FROM <alias>.
    runner = FakeRunner(scalar_response=json.dumps([{"id": "u-1"}]))
    repo = AuthRepository(runner)

    repo.create_user(email="new@tap.internal", password_hash="scrypt$...")

    sql = runner.scalar_calls[0]
    assert sql.strip().upper().startswith("WITH")
    assert "INSERT INTO users" in sql
    assert "RETURNING id" in sql


def test_create_user_returns_the_id_from_the_real_response_shape():
    runner = FakeRunner(scalar_response=json.dumps([{"id": "real-uuid-value"}]))
    repo = AuthRepository(runner)

    user_id = repo.create_user(email="new@tap.internal", password_hash="scrypt$...")

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
