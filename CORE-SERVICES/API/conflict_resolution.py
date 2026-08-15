"""
MWO-LTSA-079 -- Conflict Resolution Foundation: a pure, deterministic
comparison engine between a database snapshot and an incoming import
package, both expressed as the existing ImportPackage type (MWO-LTSA-076,
"Import Validator exists" -- reused unmodified, not redefined). No
database, no SQL, no gateway, no endpoint, no mutation anywhere in this
file -- this module only compares two already-in-memory structures and
returns a report; it never writes to either side and never calls out to
anything live.

Immutable DTO style reused from knowledge_dataclasses.py (MWO-LTSA-074,
"Knowledge Package exists"): frozen(slots=True) dataclasses, every plural
field a tuple (never a list) -- the same "real immutability, not just
frozen-dataclass surface protection" discipline that module's own header
comment establishes. Conflict/ConflictWarning-shaped field naming
(entity_type/entity_id/field/message-style fields) mirrors
import_validator.py's ImportError/ImportWarning and
recommendation_context.py's RecommendationContextEvidenceItem -- the same
established "closed vocabulary code + entity identity + real values"
shape this codebase already uses for every finding/evidence DTO, not a
new one invented here.

Resolution rule (deterministic, disclosed, never a guess or an LLM call):
  - The incoming record's primary key does not exist in the database
    snapshot at all -> CREATE_NEW (this is a new entity, not a field-level
    conflict on an existing one).
  - A field's value differs between the two sides:
      - incoming side is blank/None, database side has a real value
        -> KEEP_DATABASE (an import must never silently erase real data).
      - database side is blank/None, incoming side has a real value
        -> USE_IMPORT (filling a real gap never loses information).
      - both sides have a real, different value -> MANUAL_REVIEW (neither
        side is knowably more authoritative than the other without a
        human decision).
  - Every Conflict this engine produces has status=OPEN. RESOLVED/IGNORED
    are lifecycle states a later, separate process sets after a human (or
    a future MWO's own explicit rule) acts on a conflict -- this engine
    only ever detects and proposes, per its own "No mutation. Pure
    comparison only" rule; it never marks anything resolved itself.

Fields compared, per entity: the union of keys present on either side's
record, excluding the primary-key field itself (used only to match the
two records, never compared as its own "field conflict") -- data-driven,
not a hardcoded per-entity-type field list, so this one engine already
covers all four entity types without four near-duplicate functions (the
same "no duplicate engine" discipline this MWO's own rules require).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .import_validator import ImportPackage

RESOLUTION_KEEP_DATABASE = "KEEP_DATABASE"
RESOLUTION_USE_IMPORT = "USE_IMPORT"
RESOLUTION_MANUAL_REVIEW = "MANUAL_REVIEW"
RESOLUTION_CREATE_NEW = "CREATE_NEW"

STATUS_OPEN = "OPEN"
STATUS_RESOLVED = "RESOLVED"
STATUS_IGNORED = "IGNORED"

SEVERITY_INFO = "INFO"
SEVERITY_LOW = "LOW"
SEVERITY_HIGH = "HIGH"

# entity_type -> primary key field, matching import_validator.py's own
# duplicate-detection keys exactly (no second definition of "what
# identifies a pump/seal/installation/document" is invented here).
_PRIMARY_KEY_FIELD = {
    "pump": "tag_number",
    "seal": "seal_code",
    "installation": "installation_code",
    "document": "document_code",
}

# Sentinel field name for an entity-level (not field-level) finding --
# the incoming record's primary key does not exist in the database
# snapshot at all.
NEW_ENTITY_FIELD = "__entity__"


@dataclass(frozen=True, slots=True)
class Conflict:
    entity_type: str
    entity_id: str
    field: str
    database_value: Any
    incoming_value: Any
    resolution: str
    severity: str
    status: str


@dataclass(frozen=True, slots=True)
class ConflictReport:
    """Immutable: the full, deterministic comparison result. conflicts is
    always sorted by (entity_type, entity_id, field) -- stable output
    regardless of dict/set iteration order on either input side (this
    MWO's own "determinism" requirement)."""

    conflicts: tuple[Conflict, ...]
    conflict_count: int
    manual_review_count: int
    create_new_count: int
    has_conflicts: bool


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _index_by_key(records: tuple[dict[str, Any], ...], key_field: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record.get(key_field)
        if key:
            indexed[key] = record
    return indexed


def _compare_record(
    entity_type: str,
    entity_id: str,
    key_field: str,
    database_record: dict[str, Any],
    incoming_record: dict[str, Any],
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    fields = sorted(set(database_record) | set(incoming_record))
    for field in fields:
        if field == key_field:
            continue
        database_value = database_record.get(field)
        incoming_value = incoming_record.get(field)
        if database_value == incoming_value:
            continue

        if _is_blank(incoming_value) and not _is_blank(database_value):
            resolution, severity = RESOLUTION_KEEP_DATABASE, SEVERITY_LOW
        elif _is_blank(database_value) and not _is_blank(incoming_value):
            resolution, severity = RESOLUTION_USE_IMPORT, SEVERITY_LOW
        elif _is_blank(database_value) and _is_blank(incoming_value):
            # Both sides honestly empty in different shapes (e.g. None vs
            # "") -- not a real content conflict, nothing to propose.
            continue
        else:
            resolution, severity = RESOLUTION_MANUAL_REVIEW, SEVERITY_HIGH

        conflicts.append(
            Conflict(
                entity_type=entity_type,
                entity_id=entity_id,
                field=field,
                database_value=database_value,
                incoming_value=incoming_value,
                resolution=resolution,
                severity=severity,
                status=STATUS_OPEN,
            )
        )
    return conflicts


def _compare_entity_type(
    entity_type: str,
    database_records: tuple[dict[str, Any], ...],
    incoming_records: tuple[dict[str, Any], ...],
) -> list[Conflict]:
    key_field = _PRIMARY_KEY_FIELD[entity_type]
    database_by_key = _index_by_key(database_records, key_field)
    incoming_by_key = _index_by_key(incoming_records, key_field)

    conflicts: list[Conflict] = []
    for entity_id in sorted(incoming_by_key):
        incoming_record = incoming_by_key[entity_id]
        database_record = database_by_key.get(entity_id)

        if database_record is None:
            conflicts.append(
                Conflict(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    field=NEW_ENTITY_FIELD,
                    database_value=None,
                    incoming_value=entity_id,
                    resolution=RESOLUTION_CREATE_NEW,
                    severity=SEVERITY_INFO,
                    status=STATUS_OPEN,
                )
            )
            continue

        conflicts.extend(_compare_record(entity_type, entity_id, key_field, database_record, incoming_record))

    return conflicts


def build_conflict_report(database_snapshot: "ImportPackage", incoming_package: "ImportPackage") -> ConflictReport:
    conflicts: list[Conflict] = []
    conflicts.extend(_compare_entity_type("pump", database_snapshot.pumps, incoming_package.pumps))
    conflicts.extend(_compare_entity_type("seal", database_snapshot.seals, incoming_package.seals))
    conflicts.extend(
        _compare_entity_type("installation", database_snapshot.installations, incoming_package.installations)
    )
    conflicts.extend(_compare_entity_type("document", database_snapshot.documents, incoming_package.documents))

    # Determinism: one final, total ordering regardless of the order each
    # _compare_entity_type call happened to append in.
    conflicts.sort(key=lambda c: (c.entity_type, c.entity_id, c.field))

    manual_review_count = sum(1 for c in conflicts if c.resolution == RESOLUTION_MANUAL_REVIEW)
    create_new_count = sum(1 for c in conflicts if c.resolution == RESOLUTION_CREATE_NEW)

    return ConflictReport(
        conflicts=tuple(conflicts),
        conflict_count=len(conflicts),
        manual_review_count=manual_review_count,
        create_new_count=create_new_count,
        has_conflicts=len(conflicts) > 0,
    )


__all__ = [
    "RESOLUTION_KEEP_DATABASE",
    "RESOLUTION_USE_IMPORT",
    "RESOLUTION_MANUAL_REVIEW",
    "RESOLUTION_CREATE_NEW",
    "STATUS_OPEN",
    "STATUS_RESOLVED",
    "STATUS_IGNORED",
    "SEVERITY_INFO",
    "SEVERITY_LOW",
    "SEVERITY_HIGH",
    "NEW_ENTITY_FIELD",
    "Conflict",
    "ConflictReport",
    "build_conflict_report",
]
