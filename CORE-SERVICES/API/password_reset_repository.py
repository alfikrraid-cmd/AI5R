"""Password reset token persistence layer."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class PasswordResetRepositoryProtocol(Protocol):
    def create_reset_token(self, *, user_id: str, token_hash: str, expires_at: datetime) -> str: ...
    def consume_reset_token(self, token_hash: str) -> str | None: ...
    def get_token(self, token_hash: str) -> dict | None: ...


class PasswordResetRepository:
    def __init__(self, runner: DatabaseRunner) -> None:
        self._runner = runner

    def create_reset_token(self, *, user_id: str, token_hash: str, expires_at: datetime) -> str:
        expires_at_iso = expires_at.isoformat()
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) "
                f"VALUES ({_sql(user_id)}, {_sql(token_hash)}, {_sql(expires_at_iso)}::timestamptz) "
                "RETURNING id"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        if not rows:
            raise RuntimeError("Failed to persist password reset token")
        return rows[0]["id"]

    def consume_reset_token(self, token_hash: str) -> str | None:
        """Atomically checks that the token is not consumed and not expired,
        sets used_at = now(), and returns the user_id if valid."""
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE password_reset_tokens "
                "SET used_at = now() "
                f"WHERE token_hash = {_sql(token_hash)} "
                "AND used_at IS NULL "
                "AND expires_at > now() "
                "RETURNING user_id"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0]["user_id"] if rows else None

    def get_token(self, token_hash: str) -> dict | None:
        rows = _json_query(
            "SELECT id, user_id, token_hash, expires_at, used_at, created_at "
            f"FROM password_reset_tokens WHERE token_hash = {_sql(token_hash)}",
            self._runner,
        )
        return rows[0] if rows else None


class FakePasswordResetRepository:
    """In-memory test double for password reset repository."""

    def __init__(self) -> None:
        self.tokens: dict[str, dict] = {}
        self._id_counter = 1

    def create_reset_token(self, *, user_id: str, token_hash: str, expires_at: datetime) -> str:
        token_id = f"reset-token-{self._id_counter}"
        self._id_counter += 1
        self.tokens[token_hash] = {
            "id": token_id,
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "used_at": None,
            "created_at": datetime.now(timezone.utc),
        }
        return token_id

    def consume_reset_token(self, token_hash: str) -> str | None:
        record = self.tokens.get(token_hash)
        if not record:
            return None
        if record["used_at"] is not None:
            return None
        now = datetime.now(timezone.utc)
        expires_at = record["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            return None

        record["used_at"] = now
        return record["user_id"]

    def get_token(self, token_hash: str) -> dict | None:
        return self.tokens.get(token_hash)


__all__ = [
    "FakePasswordResetRepository",
    "PasswordResetRepository",
    "PasswordResetRepositoryProtocol",
]
