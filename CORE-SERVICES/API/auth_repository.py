"""MWO-LTSA-AUTH-001 -- the real, Postgres-backed implementation of
API.auth_service.AuthRepositoryProtocol.

Reuses the existing DatabaseRunner/_sql/_json_query machinery from
PRODUCTS/LTSA-BRAIN/INGESTION/ltsa_pump_inventory_db_upsert.py unmodified
-- the same SQL-building convention API.import_session_repository.py
already established for durable persistence -- rather than a second SQL
layer. No n8n workflow/gateway is created for this: users/organizations/
organization_memberships are new, auth-only tables with no existing
n8n workflow to route through, and gateway-per-table would be far more
machinery than a handful of read/insert queries need.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .auth_service import MembershipRecord, UserRecord  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class AuthRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    # --- reads (AuthRepositoryProtocol) -----------------------------------

    def find_user_by_email(self, email: str) -> UserRecord | None:
        rows = _json_query(
            f"SELECT id, email, password_hash, status FROM users WHERE email = {_sql(email)}",
            self._runner,
        )
        return _row_to_user(rows[0]) if rows else None

    def find_user_by_id(self, user_id: str) -> UserRecord | None:
        rows = _json_query(
            f"SELECT id, email, password_hash, status FROM users WHERE id = {_sql(user_id)}",
            self._runner,
        )
        return _row_to_user(rows[0]) if rows else None

    def find_active_membership_for_user(self, user_id: str) -> MembershipRecord | None:
        rows = _json_query(
            "SELECT m.organization_id, o.code AS organization_code, m.role, m.status "
            "FROM organization_memberships m "
            "JOIN organizations o ON o.id = m.organization_id "
            f"WHERE m.user_id = {_sql(user_id)} AND m.status = 'ACTIVE' "
            "ORDER BY m.created_at ASC LIMIT 1",
            self._runner,
        )
        return _row_to_membership(rows[0]) if rows else None

    def find_membership(self, user_id: str, organization_id: str) -> MembershipRecord | None:
        rows = _json_query(
            "SELECT m.organization_id, o.code AS organization_code, m.role, m.status "
            "FROM organization_memberships m "
            "JOIN organizations o ON o.id = m.organization_id "
            f"WHERE m.user_id = {_sql(user_id)} AND m.organization_id = {_sql(organization_id)}",
            self._runner,
        )
        return _row_to_membership(rows[0]) if rows else None

    def find_organization_by_code(self, code: str) -> str | None:
        """Returns the organization id for a canonical code (TAP/
        PERTAMINA_RU_II) -- used only by the bootstrap-admin script, not
        by any request-time auth path."""
        rows = _json_query(
            f"SELECT id FROM organizations WHERE code = {_sql(code)}", self._runner
        )
        return rows[0]["id"] if rows else None

    # --- writes (bootstrap-admin only; never called on the request path) --

    def create_user(self, *, email: str, password_hash: str) -> str:
        rows = _json_query(
            "INSERT INTO users (email, password_hash) VALUES "
            f"({_sql(email)}, {_sql(password_hash)}) "
            "RETURNING id",
            self._runner,
        )
        return rows[0]["id"]

    def create_membership(self, *, user_id: str, organization_id: str, role: str) -> None:
        self._runner.execute_script(
            "INSERT INTO organization_memberships (user_id, organization_id, role) VALUES "
            f"({_sql(user_id)}, {_sql(organization_id)}, {_sql(role)}) "
            "ON CONFLICT (user_id, organization_id) DO NOTHING;"
        )


def _row_to_user(row: dict) -> UserRecord:
    return UserRecord(id=row["id"], email=row["email"], password_hash=row["password_hash"], status=row["status"])


def _row_to_membership(row: dict) -> MembershipRecord:
    return MembershipRecord(
        organization_id=row["organization_id"],
        organization_code=row["organization_code"],
        role=row["role"],
        status=row["status"],
    )


__all__ = ["AuthRepository"]
