"""
MWO-LTSA-081 -- Import Execution Engine: the canonical write stage sitting
on top of three already-existing, unmodified layers this MWO explicitly
forbids touching:
  - Import Validator      (MWO-076, import_validator.py)       -- structural validity
  - Import Session        (MWO-077, import_session.py)          -- session identity/statistics
  - Conflict Resolution    (MWO-079, conflict_resolution.py)     -- database-vs-incoming diff
  - Knowledge Manufacturing (MWO-074, KNOWLEDGE-MANUFACTURING-PACK) -- CanonicalKnowledgePackage

This module performs the one thing none of the above does: it actually
writes Pump/Seal/Installation/Engineering-Document rows, inside one atomic
transaction, and reports what happened. Nothing here recomputes validation
or conflicts -- both are taken as already-built inputs (same "pure function
of an already-built upstream object" composition style
recommendation_context.py/import_session.py already established).

--------------------------------------------------------------------------
ARCHITECTURE DECISION (disclosed, not silent): which "repository" is
reused for the write?
--------------------------------------------------------------------------
Two candidate "repository" layers exist in this codebase:

  1. The n8n-webhook Gateways (pump_gateway.py, seal_gateway.py,
     seal_engineering_document_gateway.py, installation_gateway.py, ...).
     Confirmed by direct inspection: each is a pure HTTP transport
     (urllib request/response) to an independent n8n webhook call. There
     is no session or transaction context that spans two Gateway calls --
     each HTTP request is its own isolated round-trip. This makes them
     architecturally INCAPABLE of the "Atomic transaction only. Rollback
     on any failure." requirement, regardless of how they are used: you
     cannot BEGIN/COMMIT/ROLLBACK across independent HTTP requests. Also,
     as found during this MWO's own archaeology, InstallationGateway
     (confirmed by reading it) exposes only list_installations/
     get_installation -- no create/update method exists for Installation
     at all today.
  2. The direct-Postgres transaction pattern already established by
     PRODUCTS/LTSA-BRAIN/INGESTION/ltsa_pump_inventory_db_upsert.py's
     `DatabaseRunner`/`DatabaseConfig` (docker compose exec psql, one
     `BEGIN; ...; COMMIT;` script per apply, `-v ON_ERROR_STOP=1` so a
     mid-script failure aborts before COMMIT and the still-open
     transaction is rolled back automatically when the psql session ends)
     -- already proven end-to-end against the real runtime database this
     session (HOC PM/CM ingestion, MWO-LTSA-HOC-PM-CM).

Given requirement 1 (Gateways) is architecturally unable to satisfy the
explicit "Atomic transaction... Rollback on any failure" rule no matter
how it is invoked, and requirement 2 (DatabaseRunner) is the only
mechanism in this codebase that actually provides BEGIN/COMMIT/ROLLBACK
semantics, this engine reuses `DatabaseRunner`/`DatabaseConfig` (imported
unmodified) plus the exact same scalar-escaping SQL-building convention
(`_sql`, `_build_update`, `parse_shaft_size`, imported unmodified from
ltsa_pump_inventory_db_upsert.py; `_sql_jsonb` imported unmodified from
ltsa_hoc_pm_cm_db_upsert.py) rather than the Gateway HTTP layer. This is a
"reuse before create" choice about WHICH existing repository fits the
actual requirement, not a new engine -- no SQL-building or transaction
logic is duplicated; the only genuinely new code below is a small,
GENERIC insert-statement builder (`_build_insert`), since no existing
module had one (every existing INSERT is hand-written per fixed column
list).

--------------------------------------------------------------------------
PIPELINE
--------------------------------------------------------------------------
  Validate                     (validation, an already-built ValidatedImportPackage)
  -> Reject if validation invalid       (validation.summary.is_valid is False)
  -> Reject if unresolved HIGH conflicts (any OPEN, SEVERITY_HIGH Conflict)
  -> Begin Transaction          (one BEGIN;...;COMMIT; script)
  -> Insert / Update             Pump, Seal, Installation, Engineering Document
  -> Commit
  -> Return execution report    (ImportExecutionResult; rollback happens
                                  automatically -- see DatabaseRunner note
                                  above -- if any statement fails first)

INSERT vs UPDATE vs SKIP is derived ENTIRELY from the already-built
ConflictReport, never re-decided here:
  - A Conflict with resolution=CREATE_NEW for (entity_type, entity_id)
    -> INSERT the full row.
  - A Conflict with resolution=USE_IMPORT for a specific field
    -> UPDATE that field only (the DB side was blank, the incoming side
    has a real value -- the exact blanks-only-fill policy
    ltsa_pump_inventory_db_upsert.py::_merge_fields already established,
    here literally driven by ConflictReport rather than re-diffed).
  - No conflict at all for an existing entity (both sides already equal)
    -> SKIP. This is what makes a second, unchanged import idempotent:
    once the database matches the incoming package, a freshly rebuilt
    ConflictReport (built by the caller against the now-current database
    snapshot, per conflict_resolution.py's own contract) contains zero
    conflicts for that entity, so nothing is written the second time.
  - A KEEP_DATABASE conflict alone -> SKIP (the DB's real value is never
    overwritten by a blank).
  - A resolved/ignored MANUAL_REVIEW conflict (status != OPEN -- an OPEN
    HIGH one would already have rejected the whole import above) has no
    machine-actionable resolved_value on the current Conflict shape
    (conflict_resolution.py, MWO-079) -- this engine conservatively never
    writes for it, disclosed here rather than guessed. Applying a human's
    specific resolved value is future MWO scope, not invented here.

Statistics are per entity type (pump/seal/installation/document), each
Inserted/Updated/Skipped/Failed, and are always len()/count()-derived from
the real plan and the real outcome, never separately tracked (same
"summary" discipline import_validator.ImportSummary/import_session.
ImportSessionStatistics already established). On any transaction failure,
every row that was INSERTED/UPDATED in the plan (not the SKIPPED ones)
moves to Failed -- nothing was actually persisted, so counting any of them
as succeeded would misreport an atomic all-or-nothing outcome as if it
were partial.

Audit: `execution_log` is a plain, returned tuple of ImportExecutionLogEntry
-- in-memory only. No audit table is created or written to, per this
MWO's explicit "Return execution log only. Do not build audit table."
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from conflict_resolution import Conflict, ConflictReport
    from import_session import ImportSession
    from import_validator import ValidatedImportPackage

    _KMP_PATH = (
        Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "KNOWLEDGE-MANUFACTURING-PACK"
    )
    if str(_KMP_PATH) not in sys.path:
        sys.path.insert(0, str(_KMP_PATH))
    from knowledge_dataclasses import CanonicalKnowledgePackage  # noqa: F401

# --- Real runtime imports (this module DOES call these, unlike the
# TYPE_CHECKING-only references above) -------------------------------------

# knowledge_pipeline.py's own import chain reaches FACTORY.RESOLUTION
# (AI5R-SDK). Under pytest this is already on path via the repo's own
# pytest.ini (`pythonpath = AI5R-SDK`); added here too so this module
# also works when imported outside pytest.
_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

# Closed vocabulary reused from conflict_resolution.py (MWO-079) unmodified
# -- "No hardcode": this engine's own INSERT-vs-UPDATE-vs-SKIP branching
# reads these constants, never a bare string literal duplicating them.
# Relative import (MWO-LTSA-085 fix), not a bare/sys.path-shimmed one:
# this module is always loaded as `API.import_execution_engine` by every
# real caller. A bare `from conflict_resolution import ...` would create a
# SECOND, separately-cached module object distinct from
# `API.conflict_resolution` -- harmless for these particular string
# constants (string equality doesn't care which module defined the
# literal), but the exact same class of bug that broke PlannedWrite
# equality across import paths (see import_session.py's own note) if this
# module's `Conflict`/`ConflictReport` type references were ever compared
# by value against an `API.conflict_resolution`-imported instance
# elsewhere. Fixed proactively, consistent with conflict_resolution.py's
# own established `from .import_validator import ImportPackage` pattern.
from .conflict_resolution import (  # noqa: E402
    NEW_ENTITY_FIELD,
    RESOLUTION_CREATE_NEW,
    RESOLUTION_USE_IMPORT,
    SEVERITY_HIGH,
    STATUS_OPEN,
)

_INGESTION_PATH = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

from ltsa_hoc_pm_cm_db_upsert import _sql_jsonb  # noqa: E402
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner  # noqa: E402
from ltsa_pump_inventory_db_upsert import _build_update, _sql, parse_shaft_size  # noqa: E402

_KMP_RUNTIME_PATH = (
    Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "KNOWLEDGE-MANUFACTURING-PACK"
)
if str(_KMP_RUNTIME_PATH) not in sys.path:
    sys.path.insert(0, str(_KMP_RUNTIME_PATH))

from knowledge_pipeline import to_sql_ready_dto  # noqa: E402

# object_type (conflict_resolution.py's own "entity_type") -> (table, pk_column)
_ENTITY_TABLES: dict[str, tuple[str, str]] = {
    "pump": ("ltsa_pumps", "tag_number"),
    "seal": ("seal_registry", "seal_code"),
    "installation": ("installation_report", "installation_code"),
    "document": ("seal_engineering_document", "document_code"),
}

_INSTALLATION_JSONB_COLUMNS = {
    "seal_chamber_shaft_inspection",
    "site_activities",
    "bill_of_material",
    "gland_observation",
    "sleeve_observation",
    "retainer_disc_observation",
    "cartridge_drive_collar_observation",
    "signatures",
}

_STATUS_REJECTED_INVALID = "REJECTED_INVALID"
_STATUS_REJECTED_CONFLICTS = "REJECTED_CONFLICTS"
_STATUS_COMMITTED = "COMMITTED"
_STATUS_FAILED_ROLLED_BACK = "FAILED_ROLLED_BACK"

_ACTION_INSERTED = "INSERTED"
_ACTION_UPDATED = "UPDATED"
_ACTION_SKIPPED = "SKIPPED"
_ACTION_FAILED = "FAILED"


# --- Output DTOs -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EntityExecutionStatistics:
    inserted: int
    updated: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class ImportExecutionStatistics:
    pump: EntityExecutionStatistics
    seal: EntityExecutionStatistics
    installation: EntityExecutionStatistics
    document: EntityExecutionStatistics


@dataclass(frozen=True, slots=True)
class ImportExecutionLogEntry:
    entity_type: str
    entity_id: str
    action: str
    detail: str | None


@dataclass(frozen=True, slots=True)
class ImportExecutionResult:
    """Immutable. `statistics` is None only when the import was rejected
    before any plan was even built (REJECTED_INVALID/REJECTED_CONFLICTS)
    -- an honest "never ran" rather than a fabricated all-zero report."""

    session_id: str
    status: str
    reason: str | None
    statistics: ImportExecutionStatistics | None
    execution_log: tuple[ImportExecutionLogEntry, ...]


# --- Plan (INSERT vs UPDATE vs SKIP), derived from the ConflictReport -------
#
# MWO-LTSA-085 -- PlannedWrite/build_execution_plan were previously private
# (_PlannedWrite/_build_plan). Made public here (a pure rename, zero
# behavior change -- every call site in this file updated together) so
# import_session.py can store the exact plan this engine already builds
# ("Store the plan produced by ImportExecutionEngine. Do not regenerate
# later.") without a second, duplicate plan-building implementation. This
# is the only change MWO-LTSA-085 makes to this file.


@dataclass(frozen=True, slots=True)
class PlannedWrite:
    entity_type: str
    entity_id: str
    action: str  # INSERTED | UPDATED | SKIPPED (planned, not yet executed)
    row: dict[str, Any] | None  # full row for INSERT, changed-fields-only for UPDATE, None for SKIP
    table: str
    pk_column: str


def _index_conflicts(conflicts: tuple["Conflict", ...]) -> dict[tuple[str, str], list["Conflict"]]:
    index: dict[tuple[str, str], list[Conflict]] = {}
    for conflict in conflicts:
        index.setdefault((conflict.entity_type, conflict.entity_id), []).append(conflict)
    return index


def _plan_entity(
    entity_type: str,
    entity_id: str,
    row: dict[str, Any],
    entity_conflicts: list["Conflict"],
) -> PlannedWrite:
    table, pk_column = _ENTITY_TABLES[entity_type]

    if any(c.field == NEW_ENTITY_FIELD and c.resolution == RESOLUTION_CREATE_NEW for c in entity_conflicts):
        return PlannedWrite(entity_type, entity_id, _ACTION_INSERTED, row, table, pk_column)

    use_import_fields = {c.field for c in entity_conflicts if c.resolution == RESOLUTION_USE_IMPORT}
    if use_import_fields:
        changed = {field: row.get(field) for field in use_import_fields if field in row}
        if changed:
            return PlannedWrite(entity_type, entity_id, _ACTION_UPDATED, changed, table, pk_column)

    return PlannedWrite(entity_type, entity_id, _ACTION_SKIPPED, None, table, pk_column)


def build_execution_plan(
    session: "ImportSession",
    conflicts: "ConflictReport",
) -> list[PlannedWrite]:
    conflict_index = _index_conflicts(conflicts.conflicts)
    plan: list[PlannedWrite] = []

    for entity_type in ("pump", "seal", "installation", "document"):
        seen_ids: set[str] = set()
        for package in session.packages:
            dto = to_sql_ready_dto(package)
            rows = _rows_for_entity_type(entity_type, dto)
            for row, entity_id in rows:
                if entity_id is None or entity_id in seen_ids:
                    continue  # never plan the same primary key twice within one session
                seen_ids.add(entity_id)
                entity_conflicts = conflict_index.get((entity_type, entity_id), [])
                plan.append(_plan_entity(entity_type, entity_id, row, entity_conflicts))

    return plan


def _rows_for_entity_type(entity_type: str, dto: dict[str, Any]) -> list[tuple[dict[str, Any], str | None]]:
    _table, pk_column = _ENTITY_TABLES[entity_type]
    if entity_type == "pump":
        rows = [dto["ltsa_pumps"]] if dto.get("ltsa_pumps") else []
    elif entity_type == "seal":
        rows = [dto["seal_registry"]] if dto.get("seal_registry") else []
    elif entity_type == "installation":
        rows = [dto["installation_report"]] if dto.get("installation_report") else []
    else:
        rows = list(dto.get("seal_engineering_document") or [])
    return [(row, row.get(pk_column)) for row in rows]


# --- SQL statement building (reuses _sql/_build_update/_sql_jsonb/parse_shaft_size unmodified) ---


def _sql_value_for_column(table: str, column: str, value: Any) -> str:
    if table == "installation_report" and column in _INSTALLATION_JSONB_COLUMNS:
        return _sql_jsonb(value if isinstance(value, dict) else ({"items": value} if value else None))
    if table == "seal_registry" and column == "shaft_size":
        return _sql(parse_shaft_size(value))
    return _sql(value)


def _build_insert(table: str, row: dict[str, Any]) -> str:
    # ON CONFLICT ... DO NOTHING is a defense-in-depth idempotency guard,
    # not the primary INSERT-vs-SKIP decision (that already comes from the
    # ConflictReport, built fresh by the caller before each run). Disclosed
    # edge case: if a caller passes a stale ConflictReport for a row that
    # in fact already exists, this clause silently no-ops the INSERT at
    # the SQL level, but this function's own caller still reports it as
    # "Inserted" in statistics (no per-statement RETURNING is captured
    # from a single batched script) -- correct for every case this MWO's
    # own idempotency tests exercise (always re-deriving conflicts against
    # a fresh snapshot before a second run), disclosed as a known
    # limitation rather than silently assumed correct for a stale-report
    # caller.
    columns = sorted(key for key, value in row.items() if value is not None)
    if not columns:
        columns = sorted(row.keys())
    column_list = ", ".join(columns)
    value_list = ", ".join(_sql_value_for_column(table, column, row.get(column)) for column in columns)
    pk_column = _ENTITY_TABLES_BY_TABLE[table]
    return (
        f"INSERT INTO {table} ({column_list}) VALUES ({value_list}) "
        f"ON CONFLICT ({pk_column}) DO NOTHING;"
    )


_ENTITY_TABLES_BY_TABLE = {table: pk for table, pk in _ENTITY_TABLES.values()}


def _build_update_statement(table: str, pk_column: str, pk_value: str, fields: dict[str, Any]) -> str:
    if table == "installation_report" and any(field in _INSTALLATION_JSONB_COLUMNS for field in fields):
        assignments = ", ".join(
            f"{column} = {_sql_value_for_column(table, column, value)}" for column, value in sorted(fields.items())
        )
        return f"UPDATE {table} SET {assignments}, updated_at = NOW() WHERE {pk_column} = {_sql(pk_value)};"
    if table == "seal_registry" and "shaft_size" in fields:
        fields = {**fields, "shaft_size": parse_shaft_size(fields["shaft_size"])}
    return _build_update(table, pk_column, pk_value, fields)


# --- Execution ---------------------------------------------------------------


def execute_import(
    session: "ImportSession",
    validation: "ValidatedImportPackage",
    conflicts: "ConflictReport",
    *,
    runner: DatabaseRunner,
) -> ImportExecutionResult:
    """The one entry point. Pipeline: reject-if-invalid -> reject-if-
    unresolved-HIGH-conflicts -> plan -> one atomic transaction -> report.
    `runner` is caller-supplied (constructor-injected, same convention
    PumpIdentityResolver(known_pumps=...) etc. already use) -- this
    function opens no connection of its own beyond what `runner` already
    encapsulates.
    """
    if not validation.summary.is_valid:
        return ImportExecutionResult(
            session_id=session.session_id,
            status=_STATUS_REJECTED_INVALID,
            reason=f"{validation.summary.error_count} validation error(s) present",
            statistics=None,
            execution_log=(),
        )

    unresolved_high = [c for c in conflicts.conflicts if c.severity == SEVERITY_HIGH and c.status == STATUS_OPEN]
    if unresolved_high:
        return ImportExecutionResult(
            session_id=session.session_id,
            status=_STATUS_REJECTED_CONFLICTS,
            reason=f"{len(unresolved_high)} unresolved HIGH-severity conflict(s) present",
            statistics=None,
            execution_log=(),
        )

    plan = build_execution_plan(session, conflicts)
    attempted = [item for item in plan if item.action != _ACTION_SKIPPED]

    if not attempted:
        # Nothing to write -- a fully idempotent no-op is a legitimate,
        # successful outcome, not an error. No transaction is opened
        # (there is nothing to wrap).
        return ImportExecutionResult(
            session_id=session.session_id,
            status=_STATUS_COMMITTED,
            reason=None,
            statistics=_statistics_from_plan(plan),
            execution_log=_log_from_plan(plan),
        )

    statements = ["BEGIN;"]
    for item in attempted:
        if item.action == _ACTION_INSERTED:
            statements.append(_build_insert(item.table, item.row))
        else:
            statements.append(_build_update_statement(item.table, item.pk_column, item.entity_id, item.row))
    statements.append("COMMIT;")

    try:
        runner.execute_script("\n".join(statements))
    except Exception as error:  # noqa: BLE001 -- deliberately broad: any failure means "rolled back", full stop.
        failed_plan = [
            PlannedWrite(item.entity_type, item.entity_id, _ACTION_FAILED, item.row, item.table, item.pk_column)
            if item.action != _ACTION_SKIPPED
            else item
            for item in plan
        ]
        return ImportExecutionResult(
            session_id=session.session_id,
            status=_STATUS_FAILED_ROLLED_BACK,
            reason=str(error),
            statistics=_statistics_from_plan(failed_plan),
            execution_log=_log_from_plan(failed_plan, detail=str(error)),
        )

    return ImportExecutionResult(
        session_id=session.session_id,
        status=_STATUS_COMMITTED,
        reason=None,
        statistics=_statistics_from_plan(plan),
        execution_log=_log_from_plan(plan),
    )


def _statistics_from_plan(plan: list[PlannedWrite]) -> ImportExecutionStatistics:
    def _for(entity_type: str) -> EntityExecutionStatistics:
        rows = [item for item in plan if item.entity_type == entity_type]
        return EntityExecutionStatistics(
            inserted=sum(1 for item in rows if item.action == _ACTION_INSERTED),
            updated=sum(1 for item in rows if item.action == _ACTION_UPDATED),
            skipped=sum(1 for item in rows if item.action == _ACTION_SKIPPED),
            failed=sum(1 for item in rows if item.action == _ACTION_FAILED),
        )

    return ImportExecutionStatistics(
        pump=_for("pump"), seal=_for("seal"), installation=_for("installation"), document=_for("document")
    )


def _log_from_plan(plan: list[PlannedWrite], *, detail: str | None = None) -> tuple[ImportExecutionLogEntry, ...]:
    return tuple(
        ImportExecutionLogEntry(
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            action=item.action,
            detail=detail if item.action == _ACTION_FAILED else None,
        )
        for item in plan
    )


__all__ = [
    "EntityExecutionStatistics",
    "ImportExecutionStatistics",
    "ImportExecutionLogEntry",
    "ImportExecutionResult",
    "PlannedWrite",
    "execute_import",
    "build_execution_plan",
]
