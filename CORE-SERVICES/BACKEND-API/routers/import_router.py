from __future__ import annotations

import dataclasses
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from API.conflict_resolution import build_conflict_report
from API.import_cli import dry_run_import
from API.import_queue import ImportQueueManager
from API.import_session import build_canonical_packages, build_import_session
from API.import_validator import parse_import_package, validate_import_package
from API.import_worker import ImportWorker
from dependencies import get_import_database_runner, get_import_session_repository
from FACTORY.CORE.exceptions import ManufacturingValidationError
from models.requests import (
    ImportConflictCheckRequest,
    ImportExecuteRequest,
    ImportPackageRequest,
    ImportSessionCreateRequest,
)
from models.responses import Payload

router = APIRouter()

_PUMP_XLSX_EXTENSIONS = (".xlsx", ".xls")

# Import API Foundation -- router only, no business logic: every route
# below is a thin REST wrapper around already-existing, unmodified
# functions (API.import_validator.validate_import_package, MWO-LTSA-076;
# API.conflict_resolution.build_conflict_report, MWO-LTSA-079;
# API.import_session.build_import_session, MWO-LTSA-077). Pure functions
# are called directly, not through Depends() -- the same convention
# routers/pumps.py's /knowledge endpoint already established for
# build_engineering_insight()/compute_executive_metrics(). Only the one
# stateful component (ImportSessionRepository, needed so GET .../status
# has something to read a session back from) goes through
# Depends(get_import_session_repository), matching every Gateway's own DI
# pattern in dependencies.py.
#
# MWO-LTSA-103 -- POST .../execute enabled. Chain: Depends(get_import_
# session_repository).get(session_id) -> ImportQueueManager.enqueue()
# (fresh, per-request instance -- the same "queue/worker are per-call, not
# a shared singleton" convention import_cli.py already established; only
# ImportSessionRepository/DatabaseRunner are shared, via Depends(), since
# GET .../status needs the SAME repository instance a session was written
# to) -> ImportWorker.process_all() (reused unmodified, MWO-LTSA-096) ->
# the real ImportExecutionResult it returns, serialized as-is. Depends(
# get_import_database_runner) (dependencies.py, this MWO) is the one new
# DI wiring this mission adds -- the live-DB credential gap the previous
# revision of this comment described is closed.
#
# Disclosed, not fixed here (out of this MWO's scope -- "No new engine"):
# ImportWorker.process_next() raises ValueError if session.conflict_report
# is None or session.validated_packages does not have exactly one entry
# (MWO-LTSA-096's own disclosed guard). POST .../session (above) never
# stores a conflict_report on the session it creates -- no endpoint in
# this router attaches one after the fact -- so a session created purely
# via this Foundation's own POST .../session, never touched by a test
# fixture or the CLI, will genuinely hit that guard today. This handler
# catches it and returns the same disclosed success=false shape, never a
# fabricated result and never an unhandled 500 -- attaching a conflict_
# report to an existing session is a real, separate, un-invented gap, not
# solved here.


def _to_import_package(payload: ImportPackageRequest):
    return parse_import_package(payload.model_dump())


@router.post("/api/ltsa/import/validate")
def validate_import(payload: ImportPackageRequest) -> Payload:
    package = _to_import_package(payload)
    validated = validate_import_package(package)
    return {"success": True, "data": dataclasses.asdict(validated)}


@router.post("/api/ltsa/import/conflicts")
def check_import_conflicts(payload: ImportConflictCheckRequest) -> Payload:
    database_snapshot = _to_import_package(payload.database_snapshot)
    incoming_package = _to_import_package(payload.incoming_package)
    report = build_conflict_report(database_snapshot, incoming_package)
    return {"success": True, "data": dataclasses.asdict(report)}


# MWO-LTSA-102B -- type-contract fix, not a redesign: this handler used to
# store the raw ImportPackage (`packages=(package,)`) into ImportSession.
# packages, whose declared type is tuple["CanonicalKnowledgePackage", ...]
# (import_session.py) -- a real violation, only ever latent because POST
# .../execute below never actually reached ImportExecutionEngine (see its
# own stub message). Fixed by calling API.import_session.
# build_canonical_packages() (MWO-LTSA-102B's own minimal, disclosed
# structural step -- not a new converter/bridge, see that function's own
# docstring) instead. Request/response JSON shape, URL, and every other
# behavior of this endpoint are unchanged.
#
# MWO-LTSA-103A -- ConflictReport now stored too, closing the last gap
# POST .../execute's own disclosed guard (MWO-LTSA-096/103) needed: this
# handler now also calls API.conflict_resolution.build_conflict_report()
# (reused unmodified, the same pure function POST .../conflicts already
# calls) against payload.database_snapshot (new, optional request field --
# see models/requests.py) and passes the result into build_import_session
# (already accepted a conflict_report parameter, MWO-LTSA-085 -- this
# handler simply never supplied one before). A session built by this
# endpoint now genuinely has everything ImportWorker.process_next()
# requires (exactly one ValidatedImportPackage, a real ConflictReport),
# so POST .../execute succeeds against it with no test-only fixture.
@router.post("/api/ltsa/import/session")
def create_import_session(
    payload: ImportSessionCreateRequest,
    import_session_repository=Depends(get_import_session_repository),
) -> Payload:
    package = _to_import_package(payload.package)
    validated = validate_import_package(package)

    try:
        canonical_packages = build_canonical_packages(package)
    except ManufacturingValidationError as error:
        return {"success": False, "message": str(error), "data": None}

    database_snapshot = _to_import_package(payload.database_snapshot)
    conflicts = build_conflict_report(database_snapshot, package)

    session = build_import_session(
        session_id=payload.session_id,
        created_at=payload.created_at,
        source=payload.source,
        status=payload.status,
        created_by=payload.created_by,
        packages=canonical_packages,
        validations=(validated,),
        conflict_report=conflicts,
    )
    import_session_repository.save(session)
    return {"success": True, "data": dataclasses.asdict(session)}


@router.post("/api/ltsa/import/execute")
def execute_import(
    payload: ImportExecuteRequest,
    import_session_repository=Depends(get_import_session_repository),
    database_runner=Depends(get_import_database_runner),
) -> Payload:
    session = import_session_repository.get(payload.session_id)
    if session is None:
        return {
            "success": False,
            "message": f"Import session '{payload.session_id}' not found",
            "data": None,
        }

    queue = ImportQueueManager()
    queue.enqueue(f"JOB-{uuid.uuid4()}", payload.session_id, datetime.now(timezone.utc).isoformat())
    worker = ImportWorker(queue=queue, session_repository=import_session_repository, runner=database_runner)

    try:
        results = worker.process_all()
    except ValueError as error:
        return {"success": False, "message": str(error), "data": None}

    return {"success": True, "data": dataclasses.asdict(results[0])}


@router.get("/api/ltsa/import/status/{session_id}")
def get_import_status(
    session_id: str,
    import_session_repository=Depends(get_import_session_repository),
) -> Payload:
    session = import_session_repository.get(session_id)
    if session is None:
        return {
            "success": False,
            "message": f"Import session '{session_id}' not found",
            "data": None,
        }
    return {"success": True, "data": dataclasses.asdict(session)}


# Pump Master XLSX dry-run (MWO-LTSA-DATA-IMPORT-UI-001B) -- the one new
# endpoint this mission adds, a thin multipart wrapper around
# API.import_cli.dry_run_import() (MWO-LTSA-DATA-IMPORT-UI-001A/-CLOSURE),
# reused unmodified. No new validation/conflict/planning logic lives here.
#
# Zero persistent writes: dry_run_import() itself never calls
# execute_import()/ImportWorker/runner.execute_script() -- see that
# function's own docstring. `runner` (Depends(get_import_database_runner),
# the same singleton POST .../execute already uses) is used only for the
# read-only live-snapshot query inside dry_run_import().
#
# Temporary file lifecycle: the uploaded bytes are written to a real
# NamedTemporaryFile (delete=False, since Windows cannot open an
# already-open NamedTemporaryFile a second time for ExcelReader to read)
# with the ORIGINAL filename's suffix preserved (ExcelReader/
# UniversalImportAdapter dispatch on Path.suffix, not content-sniffing --
# reused unmodified, not re-implemented here). The file is always removed
# in `finally`, whether dry_run_import succeeds, raises, or the extension
# check rejects it first -- no upload is ever left behind on disk.
@router.post("/api/ltsa/import/pump-xlsx/dry-run")
async def dry_run_pump_xlsx(
    file: UploadFile = File(...),
    database_runner=Depends(get_import_database_runner),
) -> Payload:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _PUMP_XLSX_EXTENSIONS:
        return {
            "success": False,
            "message": f"Unsupported file type '{suffix or '(none)'}' -- expected .xlsx or .xls",
            "data": None,
        }

    tmp_path: str | None = None
    try:
        contents = await file.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        report = dry_run_import(Path(tmp_path), database_runner)
        return {"success": True, "data": dataclasses.asdict(report)}
    except ManufacturingValidationError as error:
        return {"success": False, "message": str(error), "data": None}
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.remove(tmp_path)
