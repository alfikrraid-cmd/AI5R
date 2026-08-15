"""
Import API Foundation -- ImportSessionRepository: in-memory storage, now
optionally backed by Postgres (MWO-LTSA-DATA-IMPORT-UI-001C-DURABLE) so a
session survives an API process restart between Dry Run and Approve.
Every method's PUBLIC signature/behavior for a caller that never asked for
durability (no `runner` passed to __init__, or no `package`/`snapshot`
passed to create()) is byte-for-byte unchanged from before this MWO --
process-memory only, exactly as every existing test/caller already uses
it.

Storage only, not business logic: every method still does no validation,
no derivation, no decision-making beyond the status/replay bookkeeping
this MWO's own "atomic status/replay protection" requirement adds.

--------------------------------------------------------------------------
MWO-LTSA-DATA-IMPORT-UI-001C-DURABLE -- durability design
--------------------------------------------------------------------------
The durable table (CORE-SERVICES/RUNTIME/init_postgres.sql,
`import_sessions`) stores only the IMMUTABLE reviewed inputs a dry-run
produced -- `package` (the full, original ImportPackage: pumps/seals/
installations/documents, each a list of raw dicts) and `snapshot` (the
live-DB snapshot AT DRY-RUN TIME) -- plus the MUTABLE `status`/
`execution_result`. It never stores the derived ImportSession object
graph itself (CanonicalKnowledgePackage/ValidatedImportPackage/
ConflictReport/PlannedWrite -- several nested dataclass types with no
generic "rebuild from a plain dict" available anywhere in this codebase).

Reconstruction instead RE-RUNS the exact same pure, deterministic,
already-existing functions this whole Import pipeline already reuses
everywhere else (validate_import_package, build_conflict_report,
build_canonical_packages, build_import_session -- every one imported here
unmodified, none re-implemented) against those frozen inputs. Because
these functions are pure (no I/O, no randomness -- confirmed by each of
their own module headers), replaying them against the SAME package/
snapshot always produces the SAME ImportSession, field for field, as the
original dry-run built -- this is what "exact reviewed payload preserved"
and "no XLSX re-read on Approve" actually mean here: the FILE is never
touched again (only the frozen parsed data is), and neither is the live
database (only the frozen snapshot is).

Atomic replay guard: claim_for_execution() uses a single SQL
`UPDATE ... WHERE status NOT IN (...) RETURNING status` when durable
(Postgres's own row-level locking makes two concurrent claims for the
SAME session_id serialize -- the second one's WHERE clause simply no
longer matches once the first has committed) -- not a read-then-write
Python-level check, which two concurrent requests could both pass. The
in-memory-only fallback (no runner) does the equivalent check-and-set
within one Python statement -- correct for the single-process case that
mode is already scoped to, disclosed here rather than presented as
having the same cross-process guarantee.

EXECUTING (already one of import_session.py's own IMPORT_SESSION_STATUSES
-- not a new status invented for this) is the claimed-but-not-yet-
finished state: claim_for_execution() moves a session from any
non-terminal, non-EXECUTING status to EXECUTING; only IMPORTED and FAILED
are terminal (a session that failed is not silently retried -- a fresh
Dry Run is required, matching MWO-LTSA-DATA-IMPORT-UI-001C's own "FAILED
cannot silently retry" rule, carried forward here for the durable case).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

    from .import_session import ImportSession

_INGESTION_PATH = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

# Deferred (function-local) imports for the pure-function replay used by
# _reconstruct() below -- see that function's own note on why this avoids
# a real import cycle (import_session.py itself does not import this
# module, so a module-level import here would also be safe; deferred
# anyway so a caller that never uses durability pays no extra import cost
# and this module's own import graph stays exactly as light as before for
# every existing in-memory-only caller).

_TERMINAL_STATUSES = ("IMPORTED", "FAILED")
_EXECUTING_STATUS = "EXECUTING"


def _empty_package_dict() -> dict[str, list]:
    return {"pumps": [], "seals": [], "installations": [], "documents": []}


class ImportSessionRepository:
    def __init__(self, runner: "DatabaseRunner | None" = None) -> None:
        self._sessions: dict[str, "ImportSession"] = {}
        self._runner = runner

    # --- durable persistence (only exercised when self._runner is set) ---

    def _persist_new(self, session: "ImportSession", package: dict, snapshot: dict) -> None:
        if self._runner is None:
            return
        from ltsa_hoc_pm_cm_db_upsert import _sql_jsonb
        from ltsa_pump_inventory_db_upsert import _sql

        self._runner.execute_script(
            "INSERT INTO import_sessions (session_id, status, source, created_at, package, snapshot) "
            f"VALUES ({_sql(session.session_id)}, {_sql(session.status)}, {_sql(session.source)}, "
            f"{_sql(session.created_at)}, {_sql_jsonb(package)}, {_sql_jsonb(snapshot)}) "
            "ON CONFLICT (session_id) DO NOTHING;"
        )

    def _persist_update(self, session: "ImportSession") -> None:
        if self._runner is None:
            return
        import dataclasses

        from ltsa_hoc_pm_cm_db_upsert import _sql_jsonb
        from ltsa_pump_inventory_db_upsert import _sql

        execution_result = dataclasses.asdict(session.execution_result) if session.execution_result else None
        self._runner.execute_script(
            "UPDATE import_sessions SET "
            f"status = {_sql(session.status)}, "
            f"execution_result = {_sql_jsonb(execution_result)}, "
            "updated_at = now() "
            f"WHERE session_id = {_sql(session.session_id)};"
        )

    def _reconstruct(self, session_id: str) -> "ImportSession | None":
        """Reads the durable row (if any) and replays the pure functions
        described in this module's own header to rebuild the exact
        ImportSession the original dry-run produced. Returns None if no
        durable row exists (never existed, or this repository has no
        runner at all) -- a real "not found", never fabricated."""
        if self._runner is None:
            return None

        from ltsa_pump_inventory_db_upsert import _json_query

        from .conflict_resolution import build_conflict_report
        from .import_session import build_canonical_packages, build_import_session
        from .import_validator import ImportPackage, validate_import_package

        rows = _json_query(
            "SELECT session_id, status, source, created_at, package, snapshot, execution_result "
            f"FROM import_sessions WHERE session_id = '{session_id}'",
            self._runner,
        )
        if not rows:
            return None
        row = rows[0]

        def _to_package(raw: dict | None) -> "ImportPackage":
            raw = raw or _empty_package_dict()
            return ImportPackage(
                pumps=tuple(raw.get("pumps") or ()),
                seals=tuple(raw.get("seals") or ()),
                installations=tuple(raw.get("installations") or ()),
                documents=tuple(raw.get("documents") or ()),
            )

        package = _to_package(row.get("package"))
        snapshot = _to_package(row.get("snapshot"))
        # Same tag_number-is-identity filter dry_run_import() already
        # applies before planning -- reused at the same shape, not
        # re-derived differently here (a row with no tag_number has no
        # identity to plan a write against, exactly as documented there).
        plan_package = ImportPackage(
            pumps=tuple(p for p in package.pumps if (p.get("tag_number") or "").strip()),
            seals=package.seals,
            installations=package.installations,
            documents=package.documents,
        )

        validated = validate_import_package(package)
        conflicts = build_conflict_report(snapshot, plan_package)
        canonical_packages = build_canonical_packages(plan_package)

        session = build_import_session(
            session_id=row["session_id"],
            created_at=row.get("created_at") or "",
            source=row.get("source") or "",
            status=row["status"],
            packages=canonical_packages,
            validations=(validated,),
            conflict_report=conflicts,
        )
        self._sessions[session_id] = session
        return session

    # --- public CRUD (existing contract, additively extended) -----------

    def create(
        self,
        session: "ImportSession",
        *,
        package: dict[str, Any] | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> "ImportSession":
        """Stores a new session. Raises ValueError if a session with the
        same session_id already exists -- create() never silently
        overwrites (that is update()'s job).

        `package`/`snapshot` (both optional, plain dicts -- the exact
        {pumps, seals, installations, documents} shape ImportPackage
        already uses) are new in this MWO: when given AND this repository
        has a runner, the session is also durably persisted so it can be
        reconstructed after a restart. Omitting them (every existing
        caller) is unchanged in-memory-only behavior."""
        if session.session_id in self._sessions:
            raise ValueError(f"Import session '{session.session_id}' already exists")
        self._sessions[session.session_id] = session
        if package is not None and snapshot is not None:
            self._persist_new(session, package, snapshot)
        return session

    def save(self, session: "ImportSession") -> None:
        """Backward-compatible alias for create-or-replace, unchanged
        behavior from the pre-MWO-LTSA-085 shape -- import_router.py's
        existing POST .../session handler calls this exact method. Never
        durable (no package/snapshot to persist) -- matches its own
        pre-existing in-memory-only contract exactly."""
        self._sessions[session.session_id] = session

    def update(self, session: "ImportSession") -> "ImportSession":
        """Replaces an existing session (same session_id) with the new,
        already-built ImportSession the caller supplies -- typically the
        result of import_session.advance_import_session(). Raises
        ValueError if no session with that id exists yet (use create()
        for a genuinely new session).

        Also durably persists the new status/execution_result when this
        repository has a runner -- a no-op UPDATE (0 rows matched) if the
        session was never durably created (e.g. the generic JSON flow's
        save()-only sessions), never an error."""
        if session.session_id not in self._sessions:
            raise ValueError(f"Import session '{session.session_id}' does not exist")
        self._sessions[session.session_id] = session
        self._persist_update(session)
        return session

    def get(self, session_id: str) -> "ImportSession | None":
        cached = self._sessions.get(session_id)
        if cached is not None:
            return cached
        return self._reconstruct(session_id)

    def delete(self, session_id: str) -> bool:
        """Returns True if a session was actually removed, False if no
        such session existed -- an honest signal, never silently a no-op
        indistinguishable from a real deletion. In-memory cache only --
        the durable row (an audit record of what was reviewed/executed)
        is deliberately not deleted by this method."""
        return self._sessions.pop(session_id, None) is not None

    def list_sessions(self) -> tuple["ImportSession", ...]:
        """All sessions currently held IN MEMORY, in insertion order (dict
        insertion order, guaranteed since Python 3.7) -- unchanged from
        before this MWO. Does not enumerate the durable table (no existing
        caller needs "list every session ever durably created", and doing
        so would reconstruct every one of them eagerly for no consumer)."""
        return tuple(self._sessions.values())

    # --- atomic replay guard (MWO-LTSA-DATA-IMPORT-UI-001C-DURABLE) -----

    def claim_for_execution(self, session_id: str) -> tuple[bool, "ImportSession | None"]:
        """Atomically transitions a session from a non-terminal,
        non-EXECUTING status to EXECUTING. Returns (claimed, session):
          - (True, session): THIS call won the claim -- session.status is
            now EXECUTING; the caller must proceed to execute and then
            update() to IMPORTED/FAILED.
          - (False, None): no such session exists.
          - (False, session): it exists but could not be claimed --
            session.status (EXECUTING/IMPORTED/FAILED) tells the caller
            why (already running, or already terminal).

        Durability is per-SESSION, not per-repository: a session durably
        created (create() given package/snapshot) is claimed via a single
        `UPDATE ... WHERE status NOT IN (...) RETURNING ...` -- see this
        module's own header for why this is a real atomic guard across
        concurrent requests/processes, not a read-then-write race. A
        session that was only ever save()'d (the generic JSON Import
        flow, which never opts into durability -- e.g. no row in
        import_sessions at all) falls back to the equivalent
        check-and-set against the in-memory cache, same as when this
        repository has no runner at all -- correct for the single-process
        scope that path already has."""
        if self._runner is not None:
            import json

            from ltsa_pump_inventory_db_upsert import _sql

            # _json_query's own `FROM (sql) t` wrapping only works for a
            # plain SELECT -- a data-modifying UPDATE...RETURNING needs a
            # real CTE, so this builds the SELECT-over-CTE shape directly
            # rather than reusing that helper here (its own json_agg/
            # row_to_json aggregation shape IS reused, just written out
            # once more for this one genuinely different statement shape).
            claim_sql = (
                "WITH claimed AS ("
                f"  UPDATE import_sessions SET status = {_sql(_EXECUTING_STATUS)}, updated_at = now() "
                f"  WHERE session_id = {_sql(session_id)} "
                f"  AND status NOT IN ({_sql(_EXECUTING_STATUS)}, {_sql(_TERMINAL_STATUSES[0])}, {_sql(_TERMINAL_STATUSES[1])}) "
                "  RETURNING session_id"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM claimed t;"
            )
            claim_rows = json.loads(self._runner.query_scalar(claim_sql) or "[]")
            if claim_rows:
                self._sessions.pop(session_id, None)  # force reconstruction with the fresh EXECUTING status
                return True, self._reconstruct(session_id)

            # Claim failed via the durable path -- distinguish "this
            # session is durable but already EXECUTING/terminal" from
            # "this session was never durably created at all" (a
            # save()-only session, or truly unknown).
            existing_rows = json.loads(
                self._runner.query_scalar(
                    "SELECT COALESCE(json_agg(json_build_object('session_id', session_id))::text, '[]') "
                    f"FROM import_sessions WHERE session_id = {_sql(session_id)};"
                )
                or "[]"
            )
            if existing_rows:
                self._sessions.pop(session_id, None)
                return False, self._reconstruct(session_id)
            # Not durable at all -- fall through to the in-memory-only
            # check-and-set below.

        session = self._sessions.get(session_id)
        if session is None:
            return False, None
        if session.status in (_EXECUTING_STATUS, *_TERMINAL_STATUSES):
            return False, session
        from dataclasses import replace

        claimed = replace(session, status=_EXECUTING_STATUS)
        self._sessions[session_id] = claimed
        return True, claimed


__all__ = ["ImportSessionRepository"]
