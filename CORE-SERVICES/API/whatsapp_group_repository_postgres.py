"""
MWO-LTSA-TAP-GROUP-AGENT-001 Phase 2A -- production-persistent
implementation of GroupAuthorizationRepositoryProtocol, backed by the
SAME DatabaseRunner every other direct-DB repository in this codebase
already uses (PMOccurrenceRepository, InstallationReportRepository,
MechanicalSealStockRepository, ...) -- reuses the shared
_import_database_runner singleton, not a new connection/config.

Schema: PRODUCTS/LTSA-BRAIN/DATABASE/MIGRATIONS/032_create_whatsapp_group_authorization.sql
(NOT applied to any database by this MWO -- see that file's own header).
Until that migration is applied, every method here will raise on first
real use; dependencies.py's own wiring note explains the fallback.

record_seen_message()'s dedupe guarantee is enforced by Postgres itself
(INSERT ... ON CONFLICT DO NOTHING RETURNING ...), not by application
logic -- this is safe under concurrent/duplicate webhook delivery, unlike
an in-memory set, and survives process restart, container recreation, or
a server reboot because the row lives in the database, not in this
process's memory.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

import sys
from pathlib import Path

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))
from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .whatsapp_group_agent_service import GroupAuthorizationRecord, GroupNotFoundError

_COLUMNS = (
    "group_hash, display_label, status, allowed_scope, "
    "registered_by, registered_at, activated_by, activated_at, disabled_by, disabled_at"
)


def _row_to_record(row: dict) -> GroupAuthorizationRecord:
    allowed_scope = row.get("allowed_scope")
    return GroupAuthorizationRecord(
        group_hash=row["group_hash"],
        display_label=row["display_label"],
        status=row["status"],
        allowed_scope=frozenset(allowed_scope) if allowed_scope else None,
    )


class WhatsAppGroupAuthorizationRepository:
    """Real, Postgres-persistent GroupAuthorizationRepositoryProtocol
    implementation. Pipeline-facing methods (find_group_by_hash,
    record_seen_message) are the only two this Protocol requires;
    register/activate/disable are the admin-lifecycle surface a router
    calls, exactly mirroring whatsapp_registration_service.py's own
    PENDING -> ACTIVE (-> DISABLED) shape."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    # -- pipeline-facing (GroupAuthorizationRepositoryProtocol) ----------
    def find_group_by_hash(self, group_hash: str) -> GroupAuthorizationRecord | None:
        rows = _json_query(
            f"SELECT {_COLUMNS} FROM public.whatsapp_group_authorization WHERE group_hash = {_sql(group_hash)}",
            self._runner,
        )
        return _row_to_record(rows[0]) if rows else None

    def record_seen_message(self, provider_message_id: str) -> bool:
        # Atomic, race-safe: Postgres itself decides whether this is the
        # first time this id has ever been seen -- never a
        # check-then-insert race in application code.
        raw = self._runner.query_scalar(
            "WITH ins AS ("
            "INSERT INTO public.whatsapp_group_message_seen (provider_message_id) "
            f"VALUES ({_sql(provider_message_id)}) "
            "ON CONFLICT (provider_message_id) DO NOTHING "
            "RETURNING provider_message_id"
            ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
        )
        rows = json.loads(raw or "[]")
        return len(rows) > 0

    def prune_seen_messages_older_than(self, retention_days: int) -> int:
        """Bounded-retention cleanup for the dedupe ledger -- this is a
        dedupe ledger, never a conversation log, and must never grow
        unbounded. Intended to be invoked by a scheduled job, not the
        message pipeline itself. Returns the number of rows removed."""
        raw = self._runner.query_scalar(
            "WITH del AS ("
            "DELETE FROM public.whatsapp_group_message_seen "
            f"WHERE seen_at < now() - interval '{int(retention_days)} days' "
            "RETURNING provider_message_id"
            ") SELECT COUNT(*) FROM del;"
        )
        return int(raw or 0)

    # -- admin-facing (called only from the admin lifecycle router).
    # These return the FULL row (dict), not the narrowed
    # GroupAuthorizationRecord -- admin callers/tests need
    # registered_by/activated_by/disabled_by actor attribution, which the
    # pipeline-facing dataclass deliberately omits (it never needs it).
    def register_group(self, *, group_hash: str, display_label: str, registered_by: str) -> dict:
        raw = self._runner.query_scalar(
            "WITH ins AS ("
            "INSERT INTO public.whatsapp_group_authorization "
            "(group_hash, display_label, status, registered_by) "
            f"VALUES ({_sql(group_hash)}, {_sql(display_label)}, 'PENDING', {_sql(registered_by)}) "
            "ON CONFLICT (group_hash) DO NOTHING "
            f"RETURNING {_COLUMNS}"
            ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
        )
        rows = json.loads(raw or "[]")
        if not rows:
            # Already registered -- never silently re-create/reset an
            # existing group's state (which could resurrect a previously
            # DISABLED group back to PENDING by accident).
            existing_rows = _json_query(
                f"SELECT {_COLUMNS} FROM public.whatsapp_group_authorization WHERE group_hash = {_sql(group_hash)}",
                self._runner,
            )
            if existing_rows:
                return existing_rows[0]
            raise GroupNotFoundError(group_hash)
        return rows[0]

    def activate_group(self, *, group_hash: str, activated_by: str, allowed_scope: frozenset[str] | None = None) -> dict:
        scope_sql = "NULL" if allowed_scope is None else "ARRAY[" + ", ".join(_sql(a) for a in sorted(allowed_scope)) + "]"
        raw = self._runner.query_scalar(
            "WITH upd AS ("
            "UPDATE public.whatsapp_group_authorization "
            f"SET status = 'ACTIVE', activated_by = {_sql(activated_by)}, activated_at = now(), allowed_scope = {scope_sql} "
            f"WHERE group_hash = {_sql(group_hash)} "
            f"RETURNING {_COLUMNS}"
            ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
        )
        rows = json.loads(raw or "[]")
        if not rows:
            raise GroupNotFoundError(group_hash)
        return rows[0]

    def disable_group(self, *, group_hash: str, disabled_by: str) -> dict:
        raw = self._runner.query_scalar(
            "WITH upd AS ("
            "UPDATE public.whatsapp_group_authorization "
            f"SET status = 'DISABLED', disabled_by = {_sql(disabled_by)}, disabled_at = now() "
            f"WHERE group_hash = {_sql(group_hash)} "
            f"RETURNING {_COLUMNS}"
            ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
        )
        rows = json.loads(raw or "[]")
        if not rows:
            raise GroupNotFoundError(group_hash)
        return rows[0]


__all__ = ["WhatsAppGroupAuthorizationRepository"]
