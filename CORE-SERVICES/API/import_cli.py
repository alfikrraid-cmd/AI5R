"""
MWO-LTSA-102 -- Import CLI: a production command-line entry point over
already-existing, unmodified pipeline stages this MWO explicitly requires
reusing, never re-implementing:
  - Universal Import Adapter  (import_adapter.py, MWO-LTSA-089/090/091) -- file/folder -> ImportPackage
  - Import Validator          (import_validator.py, MWO-LTSA-076)       -- structural validity
  - Conflict Resolution        (conflict_resolution.py, MWO-LTSA-079)    -- database-vs-incoming diff
  - Import Session             (import_session.py, MWO-LTSA-077/085/102B) -- session identity/lifecycle,
    and MWO-LTSA-102B's own build_canonical_packages()                    -- ImportPackage -> CanonicalKnowledgePackage(s)
  - Import Session Repository  (import_session_repository.py, MWO-LTSA-085) -- session storage
  - Import Queue               (import_queue.py, MWO-LTSA-092)          -- FIFO work tracking
  - Import Worker              (import_worker.py, MWO-LTSA-096)         -- Queue -> Execute -> Update Session
  - Import Execution Engine    (import_execution_engine.py, MWO-LTSA-081) -- the actual write stage

Search for an existing CLI before writing this one (per this mission's own
"Search repo for existing CLI. Reuse if found."): PRODUCTS/LTSA-BRAIN/
INGESTION/ltsa_pump_inventory_db_upsert.py::main() is the one real,
existing CLI entry point in this codebase that already drives a
DatabaseRunner from command-line args (argparse, `--env-file`/
`--compose-file`, `def main() -> int`, `if __name__ == "__main__":
raise SystemExit(main())`). This module reuses that exact convention
(argument names, main()/SystemExit shape) rather than inventing a second
CLI style -- no click, no new argument-parsing framework, no second
DatabaseConfig/DatabaseRunner construction pattern.

--------------------------------------------------------------------------
MWO-LTSA-102C -- stale "EXECUTION BLOCKED" removed; real execution wired
--------------------------------------------------------------------------
MWO-LTSA-102's own original blocker -- no function anywhere converted a
many-entity ImportPackage into the CanonicalKnowledgePackage(s)
execute_import() requires -- was resolved by MWO-LTSA-102B, which added
API.import_session.build_canonical_packages(package) (reusing Knowledge
Manufacturing's own newly-extended manufacture_knowledge_packages() batch
entry point, not a new converter). This CLI now calls it, and drives the
real pipeline through to execute_import() via ImportWorker, for real: no
package with entities is ever silently left unexecuted again. See
build_canonical_packages()'s own docstring (import_session.py) for the
full "not a converter/bridge" rationale -- not repeated here, reused as
written.

An empty package (zero pumps/seals/installations/documents -- a
legitimately possible outcome, e.g. an empty workbook sheet) still has
nothing to execute, reported as done (exit 0), same as before.

--------------------------------------------------------------------------
Caller-supplied identity lives here, at the outermost boundary (not inside
any reused module)
--------------------------------------------------------------------------
import_session.py/import_queue.py both require caller-supplied
session_id/created_at/job_id/queued_at and contain no uuid.uuid4()/
datetime.now() call themselves, by design (this codebase's own
established discipline). This CLI is the real, human/script-invoked
caller -- exactly the same role AI5R-STUDIO/dashboard's own
ImportWorkspace.jsx already plays for the web path (crypto.randomUUID()/
new Date().toISOString(), generated once, client-side, at ITS own outer
boundary). This module does the equivalent at the CLI's own outer
boundary (uuid.uuid4()/datetime.now(timezone.utc)), never inside
import_session.py/import_queue.py themselves, which stay exactly as
deterministic as before.

--------------------------------------------------------------------------
Live database snapshot: reuses the established test-helper SQL pattern,
generalized for production (no TEST-* filter)
--------------------------------------------------------------------------
conflict_resolution.build_conflict_report() needs a `database_snapshot:
ImportPackage` -- reused unmodified, never re-implemented -- but nothing
in this codebase builds one against the LIVE database in production code
(only test-only, TEST-*-scoped private helpers exist: test_import_
execution_engine.py::_snapshot / test_import_worker.py::_snapshot /
test_import_session.py::_live_snapshot). _read_live_snapshot() below
reuses that exact SQL shape (same four SELECTs via
ltsa_pump_inventory_db_upsert._json_query, reused unmodified), with no
namespace filter -- the real, whole-table snapshot a real CLI needs. This
is data-gathering orchestration for this CLI's own use, not a second
conflict-comparison engine (conflict_resolution.py's own comparison logic
is never touched).

No SQL write happens anywhere in this file. No new validator, adapter,
session, queue, worker, execution engine, router, frontend, or schema is
created.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_API_DIR = Path(__file__).resolve().parent
if str(_API_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_API_DIR.parent))

_AI5R_SDK_PATH = _API_DIR.parents[1] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

_INGESTION_PATH = _API_DIR.parents[1] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

from API.conflict_resolution import build_conflict_report  # noqa: E402
from API.import_adapter import (  # noqa: E402
    PUMP_CANONICAL_FIELDS,
    _normalize_header,
    _SHEET_NAME_TO_ENTITY,
    parse_import_file,
)
from API.import_execution_engine import (  # noqa: E402
    _ACTION_INSERTED,
    _ACTION_SKIPPED,
    _ACTION_UPDATED,
)
from API.import_queue import ImportQueueManager  # noqa: E402
from API.import_session import build_canonical_packages, build_import_session  # noqa: E402
from API.import_session_repository import ImportSessionRepository  # noqa: E402
from API.import_validator import ImportPackage, validate_import_package  # noqa: E402
from API.import_worker import ImportWorker  # noqa: E402
from ENTERPRISE_DATA_ENGINE import ExcelReader, SourceDescriptor  # noqa: E402
from FACTORY.CORE.exceptions import ManufacturingValidationError  # noqa: E402
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _json_query  # noqa: E402

_RUNTIME_DIR = _API_DIR.parents[1] / "CORE-SERVICES" / "RUNTIME"
_DEFAULT_ENV_FILE = _RUNTIME_DIR / ".env.verify.local"
_DEFAULT_COMPOSE_FILE = _RUNTIME_DIR / "compose.yaml"

# Distinct, script-friendly process exit codes -- never all collapsed into
# a single "0 = ok, 1 = anything else" pair, so a caller can tell "your
# data is invalid" apart from "execution itself was rejected/failed" apart
# from "unsupported/unreadable input". _EXIT_EXECUTION_BLOCKED (2) is
# renamed/repurposed here (MWO-LTSA-102C) to _EXIT_EXECUTION_FAILED -- the
# old "this CLI refuses to even try" meaning is gone (the gap it described
# is closed); 2 now means "execute_import() itself rejected or rolled back
# a real attempt" (REJECTED_INVALID/REJECTED_CONFLICTS/FAILED_ROLLED_BACK).
_EXIT_OK = 0
_EXIT_VALIDATION_FAILED = 1
_EXIT_EXECUTION_FAILED = 2
_EXIT_UNSUPPORTED_INPUT = 3
_EXECUTION_SUCCESS_STATUS = "COMMITTED"


_PUMP_SNAPSHOT_COLUMNS = ", ".join(PUMP_CANONICAL_FIELDS)


def _read_live_snapshot(runner: "DatabaseRunner") -> "ImportPackage":
    """The real, whole-table live snapshot conflict_resolution.
    build_conflict_report() needs. Same SELECT shape test_import_
    execution_engine.py::_snapshot() / test_import_worker.py::_snapshot()
    already established, generalized (no TEST-* filter) for production
    use -- reused via the same _json_query helper, not re-implemented.

    Pump columns (MWO-LTSA-DATA-IMPORT-UI-001A-CLOSURE): previously only
    tag_number/area, so conflict_resolution.build_conflict_report() could
    never see a real, already-populated value in any other column -- every
    field the incoming package set beyond tag_number/area looked
    permanently blank on the database side, so a genuinely identical
    re-import always showed as USE_IMPORT/UPDATE, never SKIP. Now selects
    every field PUMP_CANONICAL_FIELDS (import_adapter.py, reused
    unmodified -- the same real ltsa_pumps columns the Excel mapping
    already supports) covers, so an unchanged existing pump correctly
    compares as no-conflict/SKIP and a genuinely changed one still compares
    as UPDATE. No field is added that import_adapter.py's own canonical
    mapping does not already recognize."""
    return ImportPackage(
        pumps=tuple(_json_query(f"SELECT {_PUMP_SNAPSHOT_COLUMNS} FROM ltsa_pumps", runner)),
        seals=tuple(_json_query("SELECT seal_code, seal_name FROM seal_registry", runner)),
        installations=tuple(
            _json_query("SELECT installation_code, report_no, source_document_name FROM installation_report", runner)
        ),
        documents=tuple(
            _json_query(
                "SELECT document_code, seal_code, document_type, title FROM seal_engineering_document", runner
            )
        ),
    )


def _entity_count(package: "ImportPackage") -> int:
    return len(package.pumps) + len(package.seals) + len(package.installations) + len(package.documents)


# --- Dry-run (MWO-LTSA-DATA-IMPORT-UI-001A) ---------------------------------
#
# Pump Master XLSX dry-run: the exact same adapt -> validate -> conflict-
# check pipeline _process_one_package() below already runs, reused
# unmodified, but stops before build_execution_plan's result (here obtained
# for free via build_import_session()'s own _derive_execution_plan,
# import_session.py -- not re-implemented) is ever handed to
# execute_import()/ImportWorker/runner.execute_script(). No INSERT, no
# UPDATE, no transaction is ever opened -- `runner` is used only for the
# read-only live-snapshot query (_read_live_snapshot, SELECT-only). Real,
# structural zero-write guarantee, not a policy choice.
#
# Tag identity: entity_id IS tag_number verbatim, compared only by exact
# string equality throughout this whole reused pipeline (import_validator.
# py's _duplicate_error, conflict_resolution.py's primary-key indexing,
# import_execution_engine.py's PlannedWrite.entity_id) -- no normalization,
# no suffix-stripping, no fuzzy matching exists anywhere in it. This is
# exactly why "101-P-10A"/"101-P-10B"/"211-P-13A"/"211-P-13AR" (real values
# in the RU II acceptance workbook) are already, structurally, four distinct
# pumps: nothing in this pipeline could ever merge them, so no new
# A/B/AR/BR-aware code is added here -- a bespoke suffix classifier would be
# exactly the kind of invented business rule this mission's own "Do not
# invent mappings/business rules" rule forbids. A genuinely missing/blank
# tag_number is instead already an ImportError (MISSING_REQUIRED_FIELD,
# import_validator.py's existing _require) -- the one "unknown/ambiguous ->
# reject" case this reused validation already covers.


@dataclass(frozen=True, slots=True)
class DryRunReport:
    """Immutable. Every count is len()/sum() of a real list this function
    already built (import_validator.ImportSummary's own discipline,
    reused) -- never separately tracked."""

    session_id: str
    source: str
    sheet: str | None
    source_count: int
    normalized_count: int
    valid_count: int
    warning_count: int
    rejected_count: int
    duplicate_count: int
    new_count: int
    update_count: int
    mapped_columns: dict[str, str]
    unmapped_columns: tuple[str, ...]
    row_issues: tuple[dict[str, Any], ...]
    preview_rows: tuple[dict[str, Any], ...]
    approval_ready: bool


# MWO-LTSA-DATA-IMPORT-UI-001B: "preview rows" for the UI -- a real slice
# of package.pumps (already parsed, already normalized -- nothing new is
# computed for this), never a summary/fabrication of it. Capped so a
# 244-row real file doesn't ship its entire body over the API on every
# dry-run call; every row (not just this preview) is still counted in
# source_count/normalized_count, and every INVALID row still appears in
# full in row_issues regardless of this cap -- "never silently discard
# rows" is about not hiding a row's EXISTENCE/ISSUES, not about the
# preview table showing all 244 at once.
_PREVIEW_ROW_LIMIT = 20


def _excel_pump_sheet_info(path: Path) -> tuple[str | None, int, tuple[Any, ...]]:
    """Reuses ExcelReader (ENTERPRISE_DATA_ENGINE, unmodified -- the same
    reader ExcelImportAdapter.parse() itself calls) and the real
    _SHEET_NAME_TO_ENTITY table (import_adapter.py, unmodified) to report
    which worksheet(s) mapped to the "pumps" entity and their raw row
    count, without re-mapping columns or duplicating ExcelImportAdapter's
    own sheet-detection logic. Returns (sheet_name_or_None, raw_row_count,
    header_row) -- sheet_name is None for a non-.xlsx/.xls source (no
    worksheet concept applies; source_count then equals normalized_count,
    disclosed by the caller, never guessed)."""
    if Path(path).suffix.lower() not in (".xlsx", ".xls"):
        return None, 0, ()

    dataset = ExcelReader().read(SourceDescriptor(source_id=str(path), reader_name="excel", location=str(path)))
    sheet_names: list[str] = []
    total_rows = 0
    headers: tuple[Any, ...] = ()
    for worksheet in dataset.data:
        if _SHEET_NAME_TO_ENTITY.get(_normalize_header(worksheet["name"])) != "pumps":
            continue
        rows = worksheet["rows"]
        if not rows:
            continue
        sheet_names.append(worksheet["name"])
        headers = rows[0]
        total_rows += len(rows) - 1  # exclude header row

    return (", ".join(sheet_names) or None), total_rows, headers


def dry_run_import(path: Path, runner: "DatabaseRunner", *, session_id: str | None = None) -> DryRunReport:
    """The dry-run entry point this mission adds. See this module's own
    "Dry-run" header section above for the zero-write guarantee and the
    A/B/AR/BR tag-identity rationale -- neither is re-explained here."""
    package = parse_import_file(path)
    if isinstance(package, tuple):
        raise ManufacturingValidationError(
            "Dry-run supports a single file, not a folder batch (a folder yields multiple packages)"
        )

    sheet, source_count, headers = _excel_pump_sheet_info(path)
    normalized_count = len(package.pumps)
    preview_rows = tuple(package.pumps[:_PREVIEW_ROW_LIMIT])

    canonical_by_normalized = {_normalize_header(field): field for field in PUMP_CANONICAL_FIELDS}
    mapped_columns: dict[str, str] = {}
    unmapped_columns: list[str] = []
    for header in headers:
        if header is None:
            continue
        canonical = canonical_by_normalized.get(_normalize_header(header))
        if canonical:
            mapped_columns[str(header)] = canonical
        else:
            unmapped_columns.append(str(header))

    validated = validate_import_package(package)
    resolved_session_id = session_id or f"DRYRUN-{uuid.uuid4()}"

    pump_errors = [e for e in validated.errors if e.entity_type == "pump"]
    pump_warnings = [w for w in validated.warnings if w.entity_type == "pump"]
    # Distinct rejected rows: dedup by entity_id when it is a real
    # tag_number (two errors on the same pump -> one rejected row), but a
    # missing-tag_number error has entity_id=None (import_validator.py's
    # own _require) -- each such error is its own row (no shared identity
    # to dedup by), counted via the error object itself, never collapsed
    # into a single "unknown" bucket that would undercount real rejections.
    rejected_keys = {e.entity_id if e.entity_id is not None else id(e) for e in pump_errors}
    rejected_count = len(rejected_keys)
    valid_count = normalized_count - rejected_count

    # A row with no tag_number at all has no identity to plan a write
    # against -- build_canonical_packages/conflict-matching both key off
    # tag_number, so such a row is excluded from the plan below (it is
    # already fully accounted for as a rejection above, via
    # MISSING_REQUIRED_FIELD). This is the existing tag_number-is-identity
    # rule already enforced by import_validator.py/conflict_resolution.py
    # (_PRIMARY_KEY_FIELD), not a new one invented here. Every OTHER
    # structural issue (e.g. missing 'area') does not block planning --
    # matching this mission's own acceptance evidence: the real RU II
    # workbook's 5 missing-'area' rows still have a real tag_number and a
    # real new/update classification is still useful preview information
    # for them, exactly like the other 239 rows.
    identifiable_pumps = tuple(p for p in package.pumps if (p.get("tag_number") or "").strip())
    plan_package = ImportPackage(
        pumps=identifiable_pumps, seals=package.seals, installations=package.installations,
        documents=package.documents,
    )

    snapshot = _read_live_snapshot(runner)
    conflicts = build_conflict_report(snapshot, plan_package)

    try:
        canonical_packages = build_canonical_packages(plan_package)
    except ManufacturingValidationError as error:
        row_issues = ({"severity": "ERROR", "code": "CANONICAL_PACKAGE_BUILD_FAILED", "entity_id": None,
                       "field": None, "message": str(error)},)
        return DryRunReport(
            session_id=resolved_session_id,
            source=str(path),
            sheet=sheet,
            source_count=source_count or normalized_count,
            normalized_count=normalized_count,
            valid_count=0,
            warning_count=len(pump_warnings),
            rejected_count=normalized_count,
            duplicate_count=0,
            new_count=0,
            update_count=0,
            mapped_columns=mapped_columns,
            unmapped_columns=tuple(unmapped_columns),
            row_issues=row_issues,
            preview_rows=preview_rows,
            approval_ready=False,
        )

    # REVIEWING: the closest existing IMPORT_SESSION_STATUSES value
    # (import_session.py) to "validated + conflict-checked, awaiting human
    # approval" -- no new status is invented for the dry-run. validations
    # carries the REAL, full-package ValidatedImportPackage (never the
    # identity-filtered plan_package's) -- this session's own validation
    # history stays honest about everything found in the source file.
    session = build_import_session(
        session_id=resolved_session_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source=str(path),
        status="REVIEWING",
        packages=canonical_packages,
        validations=(validated,),
        conflict_report=conflicts,
    )

    pump_plan = [item for item in session.execution_plan if item.entity_type == "pump"]
    new_count = sum(1 for item in pump_plan if item.action == _ACTION_INSERTED)
    update_count = sum(1 for item in pump_plan if item.action == _ACTION_UPDATED)
    # "Duplicate" here means: already present in the live snapshot with
    # identical values across every PUMP_CANONICAL_FIELDS column
    # _read_live_snapshot() now reads (MWO-LTSA-DATA-IMPORT-UI-001A-
    # CLOSURE), so no conflict was found at all (import_execution_engine.
    # py's own SKIPPED semantics, reused verbatim -- not a new
    # classification axis).
    duplicate_count = sum(1 for item in pump_plan if item.action == _ACTION_SKIPPED)

    row_issues = tuple(
        {"severity": "ERROR", "code": e.code, "entity_id": e.entity_id, "field": e.field, "message": e.message}
        for e in pump_errors
    ) + tuple(
        {"severity": "WARNING", "code": w.code, "entity_id": w.entity_id, "field": w.field, "message": w.message}
        for w in pump_warnings
    )

    return DryRunReport(
        session_id=resolved_session_id,
        source=str(path),
        sheet=sheet,
        source_count=source_count or normalized_count,
        normalized_count=normalized_count,
        valid_count=valid_count,
        warning_count=len(pump_warnings),
        rejected_count=rejected_count,
        duplicate_count=duplicate_count,
        new_count=new_count,
        update_count=update_count,
        mapped_columns=mapped_columns,
        unmapped_columns=tuple(unmapped_columns),
        row_issues=row_issues,
        preview_rows=preview_rows,
        approval_ready=validated.summary.is_valid,
    )


def _print_dry_run_report(report: DryRunReport) -> int:
    print(f"=== DRY RUN: {report.source} ===")
    print(f"session_id={report.session_id} sheet={report.sheet}")
    print(f"source_count={report.source_count} normalized_count={report.normalized_count}")
    print(
        f"valid={report.valid_count} warning={report.warning_count} "
        f"rejected={report.rejected_count} duplicate={report.duplicate_count}"
    )
    print(f"new={report.new_count} update={report.update_count}")
    print(f"mapped_columns={report.mapped_columns}")
    print(f"unmapped_columns={report.unmapped_columns}")
    for issue in report.row_issues:
        print(f"  {issue['severity']} [{issue['code']}] {issue['entity_id']}: {issue['message']}")
    print(f"approval_ready={report.approval_ready}")
    print("DRY RUN ONLY -- zero rows were inserted or updated.")
    return _EXIT_OK if report.approval_ready else _EXIT_VALIDATION_FAILED


def _print_summary(source_label: str, package: "ImportPackage", validated, conflicts) -> None:
    print(f"=== {source_label} ===")
    print(
        f"Entities: {len(package.pumps)} pumps, {len(package.seals)} seals, "
        f"{len(package.installations)} installations, {len(package.documents)} documents"
    )
    print(
        f"Validation: valid={validated.summary.is_valid} "
        f"errors={validated.summary.error_count} warnings={validated.summary.warning_count}"
    )
    for error in validated.errors:
        print(f"  ERROR [{error.code}] {error.entity_type} '{error.entity_id}': {error.message}")
    for warning in validated.warnings:
        print(f"  WARNING [{warning.code}] {warning.entity_type} '{warning.entity_id}': {warning.message}")
    print(
        f"Conflicts: {conflicts.conflict_count} "
        f"(manual_review={conflicts.manual_review_count}, create_new={conflicts.create_new_count})"
    )
    for conflict in conflicts.conflicts:
        print(
            f"  [{conflict.resolution}] {conflict.entity_type} '{conflict.entity_id}'.{conflict.field}: "
            f"db={conflict.database_value!r} incoming={conflict.incoming_value!r}"
        )


def _print_execution_result(result) -> int:
    print(f"Execution: status={result.status} reason={result.reason}")
    if result.statistics is not None:
        for entity_type, stats in (
            ("pump", result.statistics.pump),
            ("seal", result.statistics.seal),
            ("installation", result.statistics.installation),
            ("document", result.statistics.document),
        ):
            print(
                f"  {entity_type}: inserted={stats.inserted} updated={stats.updated} "
                f"skipped={stats.skipped} failed={stats.failed}"
            )
    for entry in result.execution_log:
        print(f"  LOG {entry.entity_type} '{entry.entity_id}' {entry.action}: {entry.detail}")
    return _EXIT_OK if result.status == _EXECUTION_SUCCESS_STATUS else _EXIT_EXECUTION_FAILED


def _process_one_package(source_label: str, package: "ImportPackage", runner: "DatabaseRunner") -> int:
    validated = validate_import_package(package)
    snapshot = _read_live_snapshot(runner)
    conflicts = build_conflict_report(snapshot, package)

    _print_summary(source_label, package, validated, conflicts)

    if not validated.summary.is_valid:
        print(f"BLOCKED: {validated.summary.error_count} validation error(s) present -- cannot execute.")
        return _EXIT_VALIDATION_FAILED

    if _entity_count(package) == 0:
        print("Nothing to execute (empty package).")
        return _EXIT_OK

    # Caller-supplied identity, generated once, here at the CLI's own
    # outer boundary -- see this module's own header for why this is not
    # a violation of import_session.py/import_queue.py's own
    # no-autogeneration discipline.
    session_id = f"IMPORT-{uuid.uuid4()}"
    job_id = f"JOB-{uuid.uuid4()}"
    created_at = datetime.now(timezone.utc).isoformat()

    # MWO-LTSA-102B's own function -- ImportPackage's tuples split
    # one-entity-per-raw_document, reusing Knowledge Manufacturing's
    # batch entry point. Never re-implemented here.
    canonical_packages = build_canonical_packages(package)

    session = build_import_session(
        session_id=session_id,
        created_at=created_at,
        source=source_label,
        status="APPROVED",
        packages=canonical_packages,
        validations=(validated,),
        conflict_report=conflicts,
    )

    session_repository = ImportSessionRepository()
    session_repository.create(session)

    queue = ImportQueueManager()
    queue.enqueue(job_id, session_id, created_at)

    worker = ImportWorker(queue=queue, session_repository=session_repository, runner=runner)
    results = worker.process_all()
    result = results[0]

    final_session = session_repository.get(session_id)
    print(
        f"Session {session_id}: {len(canonical_packages)} CanonicalKnowledgePackage(s) "
        f"-> final status={final_session.status}"
    )
    return _print_execution_result(result)


def run(path: Path, runner: "DatabaseRunner", *, dry_run: bool = False) -> int:
    """The whole CLI pipeline for one input path (file or folder).
    UniversalImportAdapter.parse_import_file() returns a single
    ImportPackage for a file, or tuple[ImportPackage, ...] for a folder
    (FolderImportAdapter's own disclosed return-type divergence,
    MWO-LTSA-091) -- both are normalized to a tuple here, unmodified,
    never re-interpreted.

    dry_run=True (MWO-LTSA-DATA-IMPORT-UI-001A) routes a single file
    through dry_run_import() instead of _process_one_package() -- see
    that function's own header for the zero-write guarantee. Folder
    batches are out of this mission's scope (Pump Master XLSX is always
    one file); dry_run_import() itself raises for a folder path."""
    if dry_run:
        try:
            report = dry_run_import(path, runner)
        except (ManufacturingValidationError, NotImplementedError) as error:
            print(f"UNSUPPORTED INPUT: {error}")
            return _EXIT_UNSUPPORTED_INPUT
        return _print_dry_run_report(report)

    try:
        result = parse_import_file(path)
    except (ManufacturingValidationError, NotImplementedError) as error:
        print(f"UNSUPPORTED INPUT: {error}")
        return _EXIT_UNSUPPORTED_INPUT

    packages = result if isinstance(result, tuple) else (result,)
    if not packages:
        print(f"=== {path} ===")
        print("Nothing to execute (folder contained no supported files).")
        return _EXIT_OK

    worst_exit = _EXIT_OK
    for index, package in enumerate(packages):
        label = f"{path}" if len(packages) == 1 else f"{path} [{index + 1}/{len(packages)}]"
        exit_code = _process_one_package(label, package, runner)
        worst_exit = max(worst_exit, exit_code)
    return worst_exit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import CLI: adapt -> validate -> conflict-check -> build canonical "
            "packages -> session -> queue -> worker -> execute -> summary"
        )
    )
    parser.add_argument("path", type=Path, help="Path to a .json/.pdf/.xlsx/.xls file, or a folder")
    parser.add_argument("--env-file", type=Path, default=_DEFAULT_ENV_FILE)
    parser.add_argument("--compose-file", type=Path, default=_DEFAULT_COMPOSE_FILE)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only -- parse/validate/conflict-check/plan, zero DB writes (MWO-LTSA-DATA-IMPORT-UI-001A)",
    )
    args = parser.parse_args(argv)

    runner = DatabaseRunner(DatabaseConfig(env_file=args.env_file, compose_file=args.compose_file))
    return run(args.path, runner, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
