"""
MWO-LTSA-096 -- Import Worker: a pure, synchronous orchestrator sitting
above three already-existing, unmodified layers this MWO explicitly
requires reusing, never re-implementing:
  - Import Queue             (import_queue.py, MWO-LTSA-092)          -- WHICH job runs next
  - Import Session Repository (import_session_repository.py, MWO-LTSA-085) -- session storage
  - Import Execution Engine   (import_execution_engine.py, MWO-LTSA-081)   -- the actual write stage

Flow, per this mission's own explicit diagram: Queue -> Execute -> Update
Session. ImportWorker.process_next() does exactly three things, in order,
and nothing else:
  1. queue.dequeue()                         -- QUEUED -> RUNNING, FIFO order (reused, unmodified)
  2. execute_import(session, validation, conflicts, runner=self._runner)  -- reused, unmodified
  3. session_repository.update(advance_import_session(session, ...))     -- reused, unmodified

No validation, no conflict detection, no execution logic is duplicated
anywhere in this file -- every real decision (is this package valid? does
this field conflict? INSERT or UPDATE or SKIP?) already happened upstream,
before this worker ever sees the session, and stays exactly as that
upstream stage computed it.

--------------------------------------------------------------------------
DatabaseRunner: caller-supplied only (Chief Architect direction, this MWO)
--------------------------------------------------------------------------
execute_import() requires a live, atomic-transaction `DatabaseRunner`
(ltsa_pump_inventory_db_upsert.py, reused unmodified by
import_execution_engine.py itself -- see that module's own "ARCHITECTURE
DECISION" header for why). ImportWorker never constructs one: `runner` is
a required constructor argument, supplied by whoever wires this worker in
a real deployment -- the exact same "hold what the caller already built,
never construct it here" discipline every other module in this pipeline
(import_session.py, import_execution_engine.py, conflict_resolution.py)
already established. This keeps ImportWorker itself free of any live-DB
credential/connection logic -- the only DB-capable object anywhere in this
file is the one the caller hands in.

--------------------------------------------------------------------------
Disclosed architecture gap: session.validated_packages is a TUPLE, not the
single ValidatedImportPackage execute_import() requires (Chief Architect
direction, this MWO: "If current ImportSession does not expose exactly the
validation object required by execute_import(), STOP and disclose the
architecture gap instead of inventing an adapter.")
--------------------------------------------------------------------------
Confirmed by reading import_session.py: `ImportSession.validated_packages`
is `tuple["ValidatedImportPackage", ...]` -- one entry per package the
session was built from (import_router.py's own POST .../session handler,
the one real caller today, always builds a session with exactly one
package: `packages=(package,), validations=(validated,)`). No function
anywhere in this codebase combines multiple ValidatedImportPackage
instances into one, and this module does not invent one now -- that would
be exactly the "adapter" this mission's own instruction forbids.

What this module actually does, per that same instruction:
  - Exactly one validated package (the shape every real caller produces
    today) -- `session.validated_packages[0]` is used directly: this is
    plain tuple indexing of the one, real, already-built
    ValidatedImportPackage that session already holds verbatim, not a
    computed/adapted/fabricated stand-in.
  - Zero or more-than-one validated packages, or no conflict_report at all
    (conflict check never run for this session) -- process_next() raises
    ValueError immediately, with a message naming the exact gap, rather
    than silently combining/guessing/defaulting. This is the disclosed
    STOP this mission's own instruction requires, not a background
    failure state: it never reaches execute_import(), and no
    ImportExecutionResult is fabricated for it.

--------------------------------------------------------------------------
Queue job status: this worker updates the SESSION only, never the QUEUE
job's own status past RUNNING (disclosed, not an oversight)
--------------------------------------------------------------------------
This mission's own flow diagram is "Queue -> Execute -> Update Session" --
three steps, ending at Session, never "update the queue job". Confirmed by
reading import_queue.py: ImportQueueManager itself already discloses that
no public method transitions a job to COMPLETED/FAILED ("future MWO scope,
not invented here") -- consistent with treating the Queue as a pure
"what should run next" tracker (RUNNING = "a worker picked this up") and
ImportSession as the one authoritative record of whether an import
actually succeeded (session.status IMPORTED/FAILED, session.execution_
result). This module does not modify import_queue.py to add a job-level
COMPLETED/FAILED transition -- out of scope, not invented here either.

--------------------------------------------------------------------------
No thread, no async, no scheduler, no clock
--------------------------------------------------------------------------
process_next()/process_all() are plain, synchronous, blocking method
calls -- no threading.Thread, no asyncio, no queue.Queue, no
schedule/cron, no time.sleep, no datetime.now() anywhere in this file.
process_all() is a plain `while` loop calling process_next() until the
queue reports empty (None) -- the same "drain by repeated synchronous
call" shape any of this codebase's own tests already use, not a second
scheduler.

Deterministic: given the same queue contents, the same stored sessions,
and a runner that behaves the same way twice, process_next()/process_all()
produce equal (field-for-field) ImportExecutionResult sequences every
time -- no random id, no wall-clock timestamp, no non-deterministic
ordering (FIFO is queue.dequeue()'s own guarantee, reused unmodified).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from import_queue import ImportJob, ImportQueueManager
    from import_session_repository import ImportSessionRepository
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

    from .import_execution_engine import ImportExecutionResult

from .import_execution_engine import execute_import  # noqa: E402
from .import_session import advance_import_session  # noqa: E402

_STATUS_COMMITTED = "COMMITTED"
_SESSION_STATUS_ON_SUCCESS = "IMPORTED"
_SESSION_STATUS_ON_FAILURE = "FAILED"


class ImportWorker:
    """Queue -> Execute -> Update Session. All three collaborators are
    constructor-injected, already-existing, unmodified objects -- this
    class constructs none of them and duplicates none of their logic."""

    def __init__(
        self,
        queue: "ImportQueueManager",
        session_repository: "ImportSessionRepository",
        runner: "DatabaseRunner",
    ) -> None:
        self._queue = queue
        self._session_repository = session_repository
        self._runner = runner

    def process_next(self) -> "ImportExecutionResult | None":
        """Dequeues the next QUEUED job (FIFO, via ImportQueueManager.
        dequeue(), reused unmodified) and executes it. Returns None when
        the queue is empty -- the same honest "nothing to do" signal
        dequeue() itself already returns, never an error."""
        job = self._queue.dequeue()
        if job is None:
            return None
        return self._execute_job(job)

    def process_all(self) -> tuple["ImportExecutionResult", ...]:
        """Drains the queue: repeatedly calls process_next() until it
        returns None, in FIFO order (the same order dequeue() itself
        already guarantees), returning every ImportExecutionResult
        produced, in the order jobs were processed."""
        results: list["ImportExecutionResult"] = []
        while True:
            result = self.process_next()
            if result is None:
                break
            results.append(result)
        return tuple(results)

    def _execute_job(self, job: "ImportJob") -> "ImportExecutionResult":
        session = self._session_repository.get(job.session_id)
        if session is None:
            raise ValueError(
                f"Import session '{job.session_id}' does not exist (queued job '{job.job_id}')"
            )

        if len(session.validated_packages) != 1:
            raise ValueError(
                f"Cannot execute import session '{session.session_id}': "
                f"execute_import() requires exactly one ValidatedImportPackage, but this "
                f"session holds {len(session.validated_packages)}. ImportSession has no single "
                f"combined validation object for a zero- or multi-package session -- this is a "
                f"disclosed architecture gap (see import_worker.py's own header), not resolved "
                f"here."
            )
        if session.conflict_report is None:
            raise ValueError(
                f"Cannot execute import session '{session.session_id}': no conflict_report is "
                f"stored on this session yet (conflict check has not run for it), and "
                f"execute_import() requires one."
            )

        validation = session.validated_packages[0]
        result = execute_import(session, validation, session.conflict_report, runner=self._runner)

        next_status = _SESSION_STATUS_ON_SUCCESS if result.status == _STATUS_COMMITTED else _SESSION_STATUS_ON_FAILURE
        updated_session = advance_import_session(session, status=next_status, execution_result=result)
        self._session_repository.update(updated_session)
        return result


__all__ = ["ImportWorker"]
