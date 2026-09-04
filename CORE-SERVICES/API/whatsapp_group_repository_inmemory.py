"""
MWO-LTSA-TAP-GROUP-AGENT-001 -- disposable/local implementation of
GroupAuthorizationRepositoryProtocol. Used for CI-runnable tests and as a
Phase-1-compatible fallback (see dependencies.py's own wiring note); the
production-persistent implementation is
CORE-SERVICES/API/whatsapp_group_repository_postgres.py, backed by
PRODUCTS/LTSA-BRAIN/DATABASE/MIGRATIONS/032_create_whatsapp_group_authorization.sql
(NOT applied to any database by this MWO).

Admin-facing methods (register/activate/disable) return a plain dict with
the SAME keys the Postgres implementation's rows have (group_hash,
display_label, status, allowed_scope, registered_by, registered_at,
activated_by, activated_at, disabled_by, disabled_at) -- both
implementations are interchangeable behind the same shape, so
whatsapp_group_agent_admin.py (the admin lifecycle router) and its tests
work identically against either.

Lifecycle matches whatsapp_registration_service.py's own established
pattern: PENDING -> ACTIVE (activate_group), any state -> DISABLED
(disable_group). Registering a group (e.g. because the agent was added
to it) creates it PENDING ONLY -- it is never auto-activated, per the
mission's explicit rule ("Agent joining a group MUST NOT automatically
activate the group").
"""
from __future__ import annotations

from datetime import datetime, timezone

from .whatsapp_group_agent_service import GroupAuthorizationRecord, GroupNotFoundError

_PENDING = "PENDING"
_ACTIVE = "ACTIVE"
_DISABLED = "DISABLED"


class InMemoryGroupAuthorizationRepository:
    """Test/CI-fallback double for GroupAuthorizationRepositoryProtocol.
    State lives only in process memory -- lost on restart, by design.
    Also exposes the admin-lifecycle operations a real admin router
    calls."""

    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}
        self._seen_message_ids: dict[str, datetime] = {}

    # -- pipeline-facing (GroupAuthorizationRepositoryProtocol) ----------
    def find_group_by_hash(self, group_hash: str) -> GroupAuthorizationRecord | None:
        row = self._rows.get(group_hash)
        if row is None:
            return None
        allowed_scope = row["allowed_scope"]
        return GroupAuthorizationRecord(
            group_hash=row["group_hash"],
            display_label=row["display_label"],
            status=row["status"],
            allowed_scope=frozenset(allowed_scope) if allowed_scope else None,
        )

    def record_seen_message(self, provider_message_id: str) -> bool:
        if provider_message_id in self._seen_message_ids:
            return False
        self._seen_message_ids[provider_message_id] = datetime.now(timezone.utc)
        return True

    def prune_seen_messages_older_than(self, retention_days: int) -> int:
        cutoff = datetime.now(timezone.utc).timestamp() - retention_days * 86400
        stale = [mid for mid, seen_at in self._seen_message_ids.items() if seen_at.timestamp() < cutoff]
        for mid in stale:
            del self._seen_message_ids[mid]
        return len(stale)

    # -- admin-facing (called only from the admin lifecycle router) ------
    def register_group(self, *, group_hash: str, display_label: str, registered_by: str) -> dict:
        existing = self._rows.get(group_hash)
        if existing is not None:
            return existing
        row = {
            "group_hash": group_hash,
            "display_label": display_label,
            "status": _PENDING,
            "allowed_scope": None,
            "registered_by": registered_by,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "activated_by": None,
            "activated_at": None,
            "disabled_by": None,
            "disabled_at": None,
        }
        self._rows[group_hash] = row
        return row

    def activate_group(self, *, group_hash: str, activated_by: str, allowed_scope: frozenset[str] | None = None) -> dict:
        existing = self._rows.get(group_hash)
        if existing is None:
            raise GroupNotFoundError(group_hash)
        updated = {
            **existing,
            "status": _ACTIVE,
            "activated_by": activated_by,
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "allowed_scope": sorted(allowed_scope) if allowed_scope else None,
        }
        self._rows[group_hash] = updated
        return updated

    def disable_group(self, *, group_hash: str, disabled_by: str) -> dict:
        existing = self._rows.get(group_hash)
        if existing is None:
            raise GroupNotFoundError(group_hash)
        updated = {
            **existing,
            "status": _DISABLED,
            "disabled_by": disabled_by,
            "disabled_at": datetime.now(timezone.utc).isoformat(),
        }
        self._rows[group_hash] = updated
        return updated


__all__ = ["InMemoryGroupAuthorizationRepository"]
