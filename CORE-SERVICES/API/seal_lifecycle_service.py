"""MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001 -- the append-only physical-
seal lifecycle event ledger and its one deterministic transition engine.

seal_unit.status/current_pump_tag_number are a CURRENT-STATE snapshot
only (migration 018's own rule); this module is the ONLY code path that
writes a seal_lifecycle_event row, and it always keeps that snapshot in
sync with the event it just wrote -- in the SAME atomic transaction (see
apply_lifecycle_event's own docstring for why), never as two separate
writes a partial failure could split apart.

No MOVE event: moving a seal between pumps is REMOVE (old pump) then a
separate INSTALL (new pump) -- this module has no shortcut for it, by
design (Hard Rule: "Do not silently invent transition shortcuts").
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .seal_unit_repository import is_valid_uuid  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

EVENT_TYPES = frozenset(
    {
        "REGISTERED", "INSTALL", "REMOVE", "SEND_FOR_INSPECTION", "INSPECTION_COMPLETED",
        "SEND_FOR_REPAIR", "REPAIR_COMPLETED", "RETURN_TO_STOCK", "SCRAP",
    }
)

# Reason is required for these event types only (Hard Rule, this MWO's
# own REASON section) -- everything else may omit it.
_REASON_REQUIRED_EVENT_TYPES = frozenset({"REMOVE", "SEND_FOR_INSPECTION", "SEND_FOR_REPAIR", "SCRAP"})

_SELECT_EVENT_COLUMNS = (
    "event_id, seal_unit_id, event_type, pump_tag_number, event_at, reason, notes, "
    "source_reference, created_by, created_at"
)


class SealLifecycleError(ValueError):
    pass


class SealUnitNotFoundError(SealLifecycleError):
    pass


class InvalidLifecycleTransitionError(SealLifecycleError):
    pass


class MissingReasonError(SealLifecycleError):
    pass


class IncompatiblePumpError(SealLifecycleError):
    pass


# Per-event-type transition rule. `status_guard` is a raw SQL boolean
# expression over the locked seal_unit row's own `status` column (never
# string-interpolated user input -- these are fixed, literal fragments
# this module writes itself); `new_status`/`new_pump` describe the
# resulting current-state write. `pump_required` / `pump_must_match_
# current` implement this MWO's own explicit INSTALL/REMOVE pump rules.
_TRANSITIONS: dict[str, dict[str, Any]] = {
    "REGISTERED": {
        "status_guard": "TRUE",  # REGISTERED's real guard is "first event ever" -- handled separately below.
        "first_event_only": True,
        "new_status": None,  # unchanged -- REGISTERED never alters current state.
        "pump_required": False,
        "pump_must_match_current": False,
        "new_pump": "unchanged",
        "check_compatibility": False,
    },
    "INSTALL": {
        "status_guard": "status = 'IN_STOCK'",
        "first_event_only": False,
        "new_status": "INSTALLED",
        "pump_required": True,
        "pump_must_match_current": False,
        "new_pump": "event",
        "check_compatibility": True,
    },
    "REMOVE": {
        "status_guard": "status = 'INSTALLED'",
        "first_event_only": False,
        "new_status": "REMOVED",
        "pump_required": True,
        "pump_must_match_current": True,
        "new_pump": "null",
        "check_compatibility": False,
    },
    "SEND_FOR_INSPECTION": {
        "status_guard": "status NOT IN ('INSTALLED', 'SCRAPPED')",
        "first_event_only": False,
        "new_status": "UNDER_INSPECTION",
        "pump_required": False,
        "pump_must_match_current": False,
        "new_pump": "unchanged",
        "check_compatibility": False,
    },
    "INSPECTION_COMPLETED": {
        "status_guard": "status = 'UNDER_INSPECTION'",
        "first_event_only": False,
        "new_status": "REMOVED",
        "pump_required": False,
        "pump_must_match_current": False,
        "new_pump": "unchanged",
        "check_compatibility": False,
    },
    "SEND_FOR_REPAIR": {
        "status_guard": "status NOT IN ('INSTALLED', 'SCRAPPED')",
        "first_event_only": False,
        "new_status": "UNDER_REPAIR",
        "pump_required": False,
        "pump_must_match_current": False,
        "new_pump": "unchanged",
        "check_compatibility": False,
    },
    "REPAIR_COMPLETED": {
        "status_guard": "status = 'UNDER_REPAIR'",
        "first_event_only": False,
        "new_status": "REPAIRED",
        "pump_required": False,
        "pump_must_match_current": False,
        "new_pump": "unchanged",
        "check_compatibility": False,
    },
    "RETURN_TO_STOCK": {
        "status_guard": "status NOT IN ('INSTALLED', 'SCRAPPED')",
        "first_event_only": False,
        "new_status": "IN_STOCK",
        "pump_required": False,
        "pump_must_match_current": False,
        "new_pump": "null",
        "check_compatibility": False,
    },
    "SCRAP": {
        "status_guard": "status NOT IN ('INSTALLED', 'SCRAPPED')",
        "first_event_only": False,
        "new_status": "SCRAPPED",
        "pump_required": False,
        "pump_must_match_current": False,
        "new_pump": "null",
        "check_compatibility": False,
    },
}


def apply_lifecycle_event(
    runner: "DatabaseRunner",
    *,
    seal_unit_id: str,
    event_type: str,
    event_at: str,
    created_by: str,
    pump_tag_number: str | None = None,
    reason: str | None = None,
    notes: str | None = None,
    source_reference: str | None = None,
) -> dict:
    """The one write path for seal_lifecycle_event. ATOMICITY (this
    MWO's own CRITICAL section): the event INSERT and the seal_unit
    status/current_pump UPDATE are ONE script, executed via
    DatabaseRunner.execute_script()'s own autocommit=True + literal
    BEGIN;...COMMIT; convention (ltsa_pump_inventory_db_upsert.py's own
    documented mechanism, reused unmodified, the exact same one every
    other atomic multi-statement write in this codebase already uses) --
    a mid-script failure (guard mismatch, FK violation, CHECK violation)
    aborts before COMMIT, so neither the event nor the state change ever
    persists alone.

    CONCURRENCY: `SELECT ... FOR UPDATE` locks the seal_unit row inside
    this same transaction before any guard is evaluated, so two
    concurrent INSTALL calls on the same unit serialize -- the second
    transaction blocks until the first commits (or rolls back), then
    re-evaluates the guard against the ALREADY-UPDATED status and is
    correctly rejected if the first call already installed it.
    """
    if event_type not in EVENT_TYPES:
        raise SealLifecycleError(f"Unknown event_type: {event_type!r} (must be one of {sorted(EVENT_TYPES)})")
    if not is_valid_uuid(seal_unit_id):
        raise SealUnitNotFoundError(seal_unit_id)

    rule = _TRANSITIONS[event_type]

    if event_type in _REASON_REQUIRED_EVENT_TYPES and not (reason or "").strip():
        raise MissingReasonError(f"{event_type} requires a reason")

    if rule["pump_required"] and not pump_tag_number:
        raise SealLifecycleError(f"{event_type} requires pump_tag_number")

    status_guard_sql = rule["status_guard"]
    if rule["first_event_only"]:
        status_guard_sql = (
            f"({status_guard_sql}) AND NOT EXISTS ("
            f"SELECT 1 FROM seal_lifecycle_event WHERE seal_unit_id = locked.seal_unit_id)"
        )
    if rule["pump_must_match_current"]:
        status_guard_sql = f"({status_guard_sql}) AND current_pump_tag_number = {_sql(pump_tag_number)}"

    # Compatibility is a SEPARATE guard from status (not folded into one
    # combined boolean) so a rejection can be reported as the correct,
    # distinct error (IncompatiblePumpError vs InvalidLifecycleTransitionError)
    # rather than collapsing both causes into one generic failure.
    if rule["check_compatibility"]:
        # "If seal_pump_compatibility has authoritative rows for this
        # seal type: verify the target pump is compatible. If absent: do
        # NOT fabricate compatibility" -- absence of curated compatibility
        # data for this specific seal_code means the check is skipped
        # entirely (never treated as "incompatible"), so a production-
        # empty seal_pump_compatibility table never silently blocks every
        # future INSTALL (this MWO's own explicit instruction).
        compat_guard_sql = (
            f"NOT EXISTS (SELECT 1 FROM seal_pump_compatibility WHERE seal_code = status_ok.seal_code) "
            f"OR EXISTS (SELECT 1 FROM seal_pump_compatibility "
            f"WHERE seal_code = status_ok.seal_code AND pump_tag_number = {_sql(pump_tag_number)})"
        )
    else:
        compat_guard_sql = "TRUE"

    if rule["new_status"] is None:
        new_status_sql = "status"  # unchanged
    else:
        new_status_sql = _sql(rule["new_status"])

    if rule["new_pump"] == "event":
        new_pump_sql = _sql(pump_tag_number)
    elif rule["new_pump"] == "null":
        new_pump_sql = "NULL"
    else:
        new_pump_sql = "current_pump_tag_number"  # unchanged

    # A single compound statement (one WITH ... SELECT, even with nested
    # INSERT/UPDATE CTEs) is inherently atomic in Postgres regardless of
    # autocommit -- no explicit BEGIN;/COMMIT; needed (unlike the
    # multi-statement scripts elsewhere in this codebase that DO need it).
    # `guard` empty => event_ins/unit_upd (both SELECT FROM guard) insert/
    # update zero rows => nothing persists, matching this MWO's own
    # "if either fails, neither persists" requirement exactly.
    script = f"""
WITH locked AS (
    SELECT seal_unit_id, seal_code, status, current_pump_tag_number FROM seal_unit
    WHERE seal_unit_id = {_sql(seal_unit_id)} FOR UPDATE
),
status_ok AS (
    SELECT * FROM locked WHERE {status_guard_sql}
),
compat_ok AS (
    SELECT * FROM status_ok WHERE {compat_guard_sql}
),
event_ins AS (
    INSERT INTO seal_lifecycle_event
        (seal_unit_id, event_type, pump_tag_number, event_at, reason, notes, source_reference, created_by)
    SELECT seal_unit_id, {_sql(event_type)}, {_sql(pump_tag_number)}, {_sql(event_at)}::timestamptz,
           {_sql(reason)}, {_sql(notes)}, {_sql(source_reference)}, {_sql(created_by)}
    FROM compat_ok
    RETURNING {_SELECT_EVENT_COLUMNS}
),
unit_upd AS (
    UPDATE seal_unit SET status = {new_status_sql}, current_pump_tag_number = {new_pump_sql}, updated_at = NOW()
    WHERE seal_unit_id IN (SELECT seal_unit_id FROM compat_ok)
    RETURNING seal_unit_id
)
SELECT row_to_json(t)::text FROM (
    SELECT
        (SELECT COUNT(*) FROM locked) AS unit_found,
        (SELECT COUNT(*) FROM status_ok) AS status_matched,
        (SELECT COUNT(*) FROM compat_ok) AS compat_matched,
        COALESCE((SELECT json_agg(row_to_json(e))::text FROM event_ins e), '[]') AS event_json
) t;
"""
    raw = runner.query_scalar(script.strip())
    if not raw:
        raise SealLifecycleError("Unexpected empty result evaluating lifecycle transition")
    outcome = json.loads(raw)
    if int(outcome["unit_found"]) == 0:
        raise SealUnitNotFoundError(seal_unit_id)
    if int(outcome["status_matched"]) == 0:
        raise InvalidLifecycleTransitionError(
            f"{event_type} is not a valid transition for seal_unit {seal_unit_id} in its current state"
        )
    if int(outcome["compat_matched"]) == 0:
        raise IncompatiblePumpError(
            f"pump {pump_tag_number!r} is not listed as compatible for this seal_unit's seal_code"
        )
    events = json.loads(outcome["event_json"])
    if not events:
        raise SealLifecycleError("Unexpected: guard matched but no event was inserted")
    return events[0]


class SealLifecycleEventRepository:
    """Read-only: find/list. No update()/delete() method exists anywhere
    in this class -- append-only by omission, the same discipline
    record_change_history/seal_unit already established."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_by_id(self, event_id: str) -> dict | None:
        if not is_valid_uuid(event_id):
            return None
        rows = _json_query(
            f"SELECT {_SELECT_EVENT_COLUMNS} FROM seal_lifecycle_event WHERE event_id = {_sql(event_id)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_by_seal_unit(self, seal_unit_id: str) -> list[dict]:
        if not is_valid_uuid(seal_unit_id):
            return []
        return _json_query(
            f"SELECT {_SELECT_EVENT_COLUMNS} FROM seal_lifecycle_event "
            f"WHERE seal_unit_id = {_sql(seal_unit_id)} "
            "ORDER BY event_at ASC, event_id ASC",
            self._runner,
        )

    def list_by_pump(self, pump_tag_number: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_EVENT_COLUMNS} FROM seal_lifecycle_event "
            f"WHERE pump_tag_number = {_sql(pump_tag_number)} "
            "ORDER BY event_at ASC, event_id ASC",
            self._runner,
        )


__all__ = [
    "EVENT_TYPES",
    "SealLifecycleError",
    "SealUnitNotFoundError",
    "InvalidLifecycleTransitionError",
    "MissingReasonError",
    "IncompatiblePumpError",
    "apply_lifecycle_event",
    "SealLifecycleEventRepository",
]
