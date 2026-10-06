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
from datetime import datetime
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


# LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- every user lookup reads the same
# columns. name/last_login were previously never selected, so GET
# /api/auth/me returned name=null after a reload (Full Name fell back to the
# username); must_change_password/password_changed_at come from migration 051.
_USER_COLUMNS = (
    "id, username, name, email, password_hash, status, last_login, "
    "must_change_password, password_changed_at"
)


class AuthRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    # --- reads (AuthRepositoryProtocol) -----------------------------------

    def find_user_by_email(self, email: str) -> UserRecord | None:
        rows = _json_query(
            f"SELECT {_USER_COLUMNS} FROM users WHERE lower(email) = lower({_sql(email)})",
            self._runner,
        )
        return _row_to_user(rows[0]) if rows else None

    def find_user_by_id(self, user_id: str) -> UserRecord | None:
        rows = _json_query(
            f"SELECT {_USER_COLUMNS} FROM users WHERE id = {_sql(user_id)}",
            self._runner,
        )
        return _row_to_user(rows[0]) if rows else None

    def find_user_by_username(self, username: str) -> UserRecord | None:
        normalized = normalize_username(username)
        rows = _json_query(
            f"SELECT {_USER_COLUMNS} FROM users WHERE username = {_sql(normalized)}",
            self._runner,
        )
        return _row_to_user(rows[0]) if rows else None
    def find_active_membership_for_user(self, user_id: str) -> MembershipRecord | None:
        rows = _json_query(
            "SELECT m.organization_id, o.code AS organization_code, o.name AS organization_name, m.role, m.status, "
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
            "SELECT m.organization_id, o.code AS organization_code, o.name AS organization_name, m.role, m.status, "
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

    def find_organization_by_id(self, organization_id: str) -> str | None:
        rows = _json_query(
            f"SELECT id FROM organizations WHERE id = {_sql(organization_id)}",
            self._runner,
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
            "SELECT u.id, u.username, u.name, u.email, u.status AS user_status, "
            "u.last_login, u.created_at, u.updated_at, u.created_by, u.updated_by, "
            "m.organization_id, o.code AS organization_code, o.name AS organization_name, "
            "m.role, m.status AS membership_status "
            "FROM users u "
            "LEFT JOIN organization_memberships m ON m.user_id = u.id "
            "LEFT JOIN organizations o ON o.id = m.organization_id "
            "ORDER BY u.created_at ASC",
            self._runner,
        )

    def update_last_login(self, user_id: str) -> None:
        try:
            self._runner.execute_script(
                f"UPDATE users SET last_login = NOW() WHERE id = {_sql(user_id)};"
            )
        except Exception:
            pass

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

    def create_user(self, *, email: str | None, password_hash: str, username: str | None = None, name: str | None = None, created_by: str | None = None) -> str:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO users (username, name, email, password_hash, created_by, updated_by) VALUES "
                f"({_sql(normalize_username(username) if username is not None else None)}, {_sql(name)}, {_sql(email.lower() if email else None)}, {_sql(password_hash)}, {_sql(created_by)}, {_sql(created_by)}) "
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

    def create_user_with_membership(
        self,
        *,
        username: str,
        name: str | None = None,
        email: str | None,
        password_hash: str,
        organization_id: str,
        role: str,
        created_by: str | None = None,
        must_change_password: bool = False,
    ) -> str:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins_user AS ("
                "INSERT INTO users (username, name, email, password_hash, must_change_password, created_by, updated_by) VALUES "
                f"({_sql(normalize_username(username))}, {_sql(name)}, {_sql(email.lower() if email else None)}, {_sql(password_hash)}, {_sql(bool(must_change_password))}, {_sql(created_by)}, {_sql(created_by)}) "
                "RETURNING id"
                "), ins_membership AS ("
                "INSERT INTO organization_memberships (user_id, organization_id, role, created_by, updated_by) "
                f"SELECT id, {_sql(organization_id)}, {_sql(role)}, {_sql(created_by)}, {_sql(created_by)} FROM ins_user "
                "RETURNING user_id"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') "
                "FROM (SELECT u.id FROM ins_user u JOIN ins_membership m ON m.user_id = u.id) t;"
            )
            or "[]"
        )
        if not rows:
            raise RuntimeError("User creation did not return an id")
        return rows[0]["id"]

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

    def update_password_hash(
        self,
        user_id: str,
        password_hash: str,
        *,
        updated_by: str,
        must_change_password: bool | None = None,
        password_changed_at: datetime | None = None,
    ) -> None:
        """Administrative password reset (Phase 8) and self-service
        reset-password -- the caller has already hashed the new password
        (auth_password.hash_password()); this function never receives or
        logs a plaintext value. must_change_password / password_changed_at
        (LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A) are written in the same
        statement when given; None leaves the column unchanged."""
        extra = ""
        if must_change_password is not None:
            extra += f"must_change_password = {_sql(bool(must_change_password))}, "
        if password_changed_at is not None:
            extra += f"password_changed_at = {_sql(password_changed_at.isoformat())}::timestamptz, "
        self._runner.execute_script(
            f"UPDATE users SET password_hash = {_sql(password_hash)}, {extra}"
            f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
            f"WHERE id = {_sql(user_id)};"
        )

    def change_password(
        self,
        user_id: str,
        *,
        expected_password_hash: str,
        new_password_hash: str,
        password_changed_at: datetime,
        reason: str,
    ) -> bool:
        """Self-service change (LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A). One
        statement: the UPDATE only applies while the stored hash is still
        the one the caller just verified (a concurrent change makes it a
        no-op, returning False), clears must_change_password, records
        password_changed_at, and inserts the redacted audit row from the
        updated row, so the change and its audit record commit together."""
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                f"UPDATE users SET password_hash = {_sql(new_password_hash)}, "
                "must_change_password = FALSE, "
                f"password_changed_at = {_sql(password_changed_at.isoformat())}::timestamptz, "
                f"updated_by = {_sql(user_id)}, updated_at = NOW() "
                f"WHERE id = {_sql(user_id)} AND password_hash = {_sql(expected_password_hash)} "
                "RETURNING id"
                "), audit AS ("
                "INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                f"SELECT 'user', upd.id::text, 'password', '[REDACTED]', '[REDACTED]', upd.id, {_sql(reason)} FROM upd "
                "RETURNING entity_id"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM (SELECT id FROM upd) t;"
            )
            or "[]"
        )
        return bool(rows)

    def update_user_email(self, user_id: str, email: str, *, updated_by: str) -> None:
        """Self-service profile email update (R2B). Updates user email by authenticated ID."""
        self._runner.execute_script(
            f"UPDATE users SET email = {_sql(email.lower())}, updated_by = {_sql(updated_by)}, updated_at = NOW() "
            f"WHERE id = {_sql(user_id)};"
        )


def _row_to_user(row: dict) -> UserRecord:
    return UserRecord(
        id=row["id"],
        email=row.get("email"),
        password_hash=row["password_hash"],
        status=row["status"],
        username=row.get("username"),
        name=row.get("name"),
        last_login=str(row.get("last_login")) if row.get("last_login") is not None else None,
        must_change_password=bool(row.get("must_change_password") or False),
        password_changed_at=row.get("password_changed_at"),
    )


def _row_to_membership(row: dict) -> MembershipRecord:
    return MembershipRecord(
        organization_id=row["organization_id"],
        organization_code=row["organization_code"],
        role=row["role"],
        status=row["status"],
        data_scope_type=row.get("data_scope_type"),
        data_scope_value=row.get("data_scope_value"),
        organization_name=row.get("organization_name") or row.get("organization_code"),
    )


__all__ = ["AuthRepository"]
