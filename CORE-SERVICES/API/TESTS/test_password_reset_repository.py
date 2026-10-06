import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.password_reset_repository import (
    FakePasswordResetRepository,
    PasswordResetRepository,
)


def test_fake_password_reset_repository_create_and_consume():
    repo = FakePasswordResetRepository()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=15)

    token_id = repo.create_reset_token(user_id="user-123", token_hash="hash-abc", expires_at=expires)
    assert token_id is not None
    assert repo.get_token("hash-abc")["user_id"] == "user-123"

    # First consumption succeeds
    consumed_user = repo.consume_reset_token("hash-abc")
    assert consumed_user == "user-123"

    # Second consumption fails (single-use enforcement)
    second_consumed = repo.consume_reset_token("hash-abc")
    assert second_consumed is None


def test_fake_password_reset_repository_expired_token():
    repo = FakePasswordResetRepository()
    now = datetime.now(timezone.utc)
    expired = now - timedelta(seconds=1)

    repo.create_reset_token(user_id="user-456", token_hash="hash-expired", expires_at=expired)
    consumed_user = repo.consume_reset_token("hash-expired")
    assert consumed_user is None


def test_fake_password_reset_repository_nonexistent_token():
    repo = FakePasswordResetRepository()
    assert repo.consume_reset_token("hash-nonexistent") is None


def test_password_reset_repository_sql_queries():
    runner = MagicMock()
    runner.query_scalar.side_effect = [
        '[{"id": "tok-uuid-1"}]',
        '[{"user_id": "usr-uuid-1"}]',
    ]

    repo = PasswordResetRepository(runner)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=15)

    token_id = repo.create_reset_token(user_id="usr-uuid-1", token_hash="dummy-hash", expires_at=expires)
    assert token_id == "tok-uuid-1"
    create_call = runner.query_scalar.call_args_list[0][0][0]
    assert "INSERT INTO password_reset_tokens" in create_call
    assert "dummy-hash" in create_call

    user_id = repo.consume_reset_token("dummy-hash")
    assert user_id == "usr-uuid-1"
    consume_call = runner.query_scalar.call_args_list[1][0][0]
    assert "UPDATE password_reset_tokens" in consume_call
    assert "used_at IS NULL" in consume_call
    assert "expires_at > now()" in consume_call
