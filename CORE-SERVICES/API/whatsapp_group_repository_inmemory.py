"""
MWO-LTSA-TAP-GROUP-AGENT-001 -- Phase 1 disposable/local implementation of
GroupAuthorizationRepositoryProtocol. Explicitly NOT production
persistence: state lives only in process memory and is lost on restart.
This is intentional for Phase 1 ("design it and test using
disposable/local infrastructure only" -- no production schema change).
A real, Postgres-backed implementation is a PROPOSED, NOT-applied
migration -- see
ENGINEERING/MWO/MWO-LTSA-TAP-GROUP-AGENT-001-Proposed-Migration.md.

Lifecycle matches whatsapp_registration_service.py's own established
pattern: PENDING -> ACTIVE (activate_group), any state -> DISABLED
(disable_group). Registering a group (e.g. because the agent was added
to it) creates it PENDING ONLY -- it is never auto-activated, per the
mission's explicit rule ("Agent joining a group MUST NOT automatically
activate the group").
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from .whatsapp_group_agent_service import GroupAuthorizationRecord

_PENDING = "PENDING"
_ACTIVE = "ACTIVE"
_DISABLED = "DISABLED"


class GroupNotFoundError(ValueError):
    pass


class InMemoryGroupAuthorizationRepository:
    """Test/Phase-1 double for GroupAuthorizationRepositoryProtocol. Also
    exposes the admin-lifecycle operations (register/activate/disable) a
    future admin router would call -- kept here, not in the pipeline
    module, since the pipeline only ever needs read access
    (find_group_by_hash) and the dedupe ledger."""

    def __init__(self) -> None:
        self._groups: dict[str, GroupAuthorizationRecord] = {}
        self._audit: list[dict] = []
        self._seen_message_ids: set[str] = set()

    # -- pipeline-facing (GroupAuthorizationRepositoryProtocol) ----------
    def find_group_by_hash(self, group_hash: str) -> GroupAuthorizationRecord | None:
        return self._groups.get(group_hash)

    def record_seen_message(self, provider_message_id: str) -> bool:
        if provider_message_id in self._seen_message_ids:
            return False
        self._seen_message_ids.add(provider_message_id)
        return True

    # -- admin-facing (not wired to any router in Phase 1) ---------------
    def register_group(
        self, *, group_hash: str, display_label: str, registered_by: str
    ) -> GroupAuthorizationRecord:
        record = GroupAuthorizationRecord(group_hash=group_hash, display_label=display_label, status=_PENDING)
        self._groups[group_hash] = record
        self._audit.append(
            {
                "event": "REGISTERED",
                "group_hash": group_hash,
                "by": registered_by,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return record

    def activate_group(
        self, *, group_hash: str, activated_by: str, allowed_scope: frozenset[str] | None = None
    ) -> GroupAuthorizationRecord:
        existing = self._groups.get(group_hash)
        if existing is None:
            raise GroupNotFoundError(group_hash)
        updated = replace(existing, status=_ACTIVE, allowed_scope=allowed_scope)
        self._groups[group_hash] = updated
        self._audit.append(
            {
                "event": "ACTIVATED",
                "group_hash": group_hash,
                "by": activated_by,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return updated

    def disable_group(self, *, group_hash: str, disabled_by: str) -> GroupAuthorizationRecord:
        existing = self._groups.get(group_hash)
        if existing is None:
            raise GroupNotFoundError(group_hash)
        updated = replace(existing, status=_DISABLED)
        self._groups[group_hash] = updated
        self._audit.append(
            {
                "event": "DISABLED",
                "group_hash": group_hash,
                "by": disabled_by,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return updated


__all__ = ["InMemoryGroupAuthorizationRepository", "GroupNotFoundError"]
