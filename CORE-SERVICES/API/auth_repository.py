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

import json
from pathlib import Path
from typing import TYPE_CHECKING

import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .auth_service import MembershipRecord, UserRecord, normalize_username  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class AuthRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    # --- reads (AuthRepositoryProtocol) -----------------------------------

    def find_user_by_email(self, email: str) -> UserRecord | None:
        rows = _json_query(
            f"SELECT id, username, email, password_hash, status FROM users WHERE lower(email) = lower({_sql(email)})",
            self._runner,
        )
        return _row_to_user(rows[0]) if rows else None

    def find_user_by_id(self, user_id: str) -> UserRecord | None:
        rows = _json_query(
            f"SELECT id, username, email, password_hash, status FROM users WHERE id = {_sql(user_id)}",
            self._runner,
        )
        return _row_to_user(rows[0]) if rows else None

    def find_user_by_username(self, username: str) -> UserRecord | None:
        normalized = normalize_username(username)
        rows = _json_query(
            f"SELECT id, username, email, password_hash, status FROM users WHERE username = {_sql(normalized)}",
            self._runner,
        )
        return _row_to_user(rows[0]) if rows else None
    def find_active_membership_for_user(self, user_id: str) -> MembershipRecord | None:
        rows = _json_query(
            "SELECT m.organization_id, o.code AS organization_code, m.role, m.status, "
            "m.data_scope_type, m.data_scope_value "
            "FROM organization_memberships m "
            "JOIN organizations o ON o.id = m.organization_id "
            f"WHERE m.user_id = {_sql(user_id)} AND m.status = 'ACTIVE' "
            "ORDER BY m.created_at ASC LIMIT 1",
            self._runner,
        )
        return _row_to_membership(rows[0]) if rows else None

    def find_membership(self, user_id: str, organization_id: str) -> MembershipRecord | None:
        rows = _json_query(
            "SELECT m.organization_id, o.code AS organization_code, m.role, m.status, "
            "m.data_scope_type, m.data_scope_value "
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

    # --- MWO-LTSA-AUTH-003A-FINAL -- User Administration reads ------------

    def list_users(self) -> list[dict]:
        """One row per (user, membership) pair -- a user with more than
        one membership (not created by anything today, but not prevented
        by schema) would appear once per membership, matching the Admin
        Users UI's own per-organization row. LEFT JOIN so a user with no
        membership yet (mid-creation) still appears."""
        return _json_query(
            "SELECT u.id, u.username, u.email, u.status AS user_status, "
            "u.created_at, u.updated_at, u.created_by, u.updated_by, "
            "m.organization_id, o.code AS organization_code, o.name AS organization_name, "
            "m.role, m.status AS membership_status "
            "FROM users u "
            "LEFT JOIN organization_memberships m ON m.user_id = u.id "
            "LEFT JOIN organizations o ON o.id = m.organization_id "
            "ORDER BY u.created_at ASC",
            self._runner,
        )

    def count_active_superusers(self) -> int:
        """Last-SUPERUSER-safety's own source of truth -- always the CURRENT
        count, queried fresh immediately before any disable/demote action
        (auth_admin_service.guard_last_superuser expects the pre-action
        count)."""
        rows = _json_query(
            "SELECT count(*) AS n FROM organization_memberships m "
            "JOIN users u ON u.id = m.user_id "
            "WHERE m.role = 'SUPERUSER' AND m.status = 'ACTIVE' AND u.status = 'ACTIVE'",
            self._runner,
        )
        return int(rows[0]["n"]) if rows else 0

    def is_active_superuser(self, user_id: str) -> bool:
        rows = _json_query(
            "SELECT count(*) AS n FROM organization_memberships m "
            "JOIN users u ON u.id = m.user_id "
            f"WHERE m.user_id = {_sql(user_id)} AND m.role = 'SUPERUSER' "
            "AND m.status = 'ACTIVE' AND u.status = 'ACTIVE'",
            self._runner,
        )
        return bool(rows) and int(rows[0]["n"]) > 0

    # --- writes (bootstrap-admin script + the new Admin Users router;
    # never called on the ordinary request path) ---------------------------

    def create_user(self, *, email: str | None, password_hash: str, username: str | None = None, created_by: str | None = None) -> str:
        # MWO-LTSA-AUTH-001A -- _json_query's own `FROM (sql) t` wrapping
        # only works for a plain SELECT; a data-modifying INSERT...
        # RETURNING needs a real CTE (same fix shape as
        # import_session_repository.py's claim_for_execution()). Caught
        # against real Postgres (Task 5) -- every prior test used a fake
        # repository, which can't surface an invalid-SQL bug like this.
        #
        # MWO-LTSA-AUTH-003A-FINAL -- created_by/updated_by (migration
        # 012); created_by defaults to NULL (the bootstrap-admin script's
        # own first-user case, no prior authenticated actor exists yet;
        # _sql(None) already renders NULL). updated_by is set equal to
        # created_by at INSERT time (the creator is, trivially, also the
        # first "last editor") -- never overwritten on subsequent reads,
        # only on a real later UPDATE (Hard Rule 19: creator is never
        # overwritten by a later editor -- created_by itself is never
        # touched by update_user_status/update_membership_role/
        # update_password_hash below).
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO users (username, email, password_hash, created_by, updated_by) VALUES "
                f"({_sql(normalize_username(username) if username is not None else None)}, {_sql(email.lower() if email else None)}, {_sql(password_hash)}, {_sql(created_by)}, {_sql(created_by)}) "
                "RETURNING id"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]["id"]

    def create_membership(
        self, *, user_id: str, organization_id: str, role: str, created_by: str | None = None
    ) -> None:
        self._runner.execute_script(
            "INSERT INTO organization_memberships (user_id, organization_id, role, created_by, updated_by) VALUES "
            f"({_sql(user_id)}, {_sql(organization_id)}, {_sql(role)}, {_sql(created_by)}, {_sql(created_by)}) "
            "ON CONFLICT (user_id, organization_id) DO NOTHING;"
        )

    def update_user_status(self, user_id: str, status: str, *, updated_by: str) -> None:
        """Enable/disable (Phase 7). Never DELETEs -- FK integrity and
        historical attribution (this user may be a created_by/updated_by
        on other rows, or an installation_report reviewer) must remain
        resolvable after disabling."""
        self._runner.execute_script(
            f"UPDATE users SET status = {_sql(status)}, updated_by = {_sql(updated_by)}, updated_at = NOW() "
            f"WHERE id = {_sql(user_id)};"
        )

    def update_membership_role(self, user_id: str, organization_id: str, role: str, *, updated_by: str) -> None:
        self._runner.execute_script(
            f"UPDATE organization_memberships SET role = {_sql(role)}, "
            f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
            f"WHERE user_id = {_sql(user_id)} AND organization_id = {_sql(organization_id)};"
        )

    def update_password_hash(self, user_id: str, password_hash: str, *, updated_by: str) -> None:
        """Administrative password reset (Phase 8) -- the caller has
        already hashed the new password (auth_password.hash_password());
        this function never receives or logs a plaintext value."""
        self._runner.execute_script(
            f"UPDATE users SET password_hash = {_sql(password_hash)}, "
            f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
            f"WHERE id = {_sql(user_id)};"
        )


def _row_to_user(row: dict) -> UserRecord:
    return UserRecord(id=row["id"], email=row.get("email"), password_hash=row["password_hash"], status=row["status"], username=row.get("username"))


def _row_to_membership(row: dict) -> MembershipRecord:
    return MembershipRecord(
        organization_id=row["organization_id"],
        organization_code=row["organization_code"],
        role=row["role"],
        status=row["status"],
        data_scope_type=row.get("data_scope_type"),
        data_scope_value=row.get("data_scope_value"),
    )


__all__ = ["AuthRepository"]
