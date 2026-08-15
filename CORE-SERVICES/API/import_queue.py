"""
MWO-LTSA-092 -- Import Queue Foundation: a pure, in-memory FIFO queue of
ImportJob records sitting above three already-existing, unmodified layers
this MWO explicitly forbids touching:
  - Import Session          (import_session.py, MWO-077/085)          -- session identity/lifecycle
  - Import Execution Engine  (import_execution_engine.py, MWO-081/085) -- the actual write stage
  - Import Validator         (import_validator.py, MWO-076)            -- structural validity

This module does not validate, resolve conflicts, or execute anything --
it only orders and tracks work. An ImportJob references a session_id (the
existing ImportSession identity, import_session.py) as the unit of work;
this module never inspects, rebuilds, or requires an actual ImportSession
instance -- session_id is an opaque caller-supplied string, exactly the
same "hold what the caller already built, never re-derive it" discipline
import_session.py/conflict_resolution.py/import_execution_engine.py
already established.

--------------------------------------------------------------------------
Scope boundary (disclosed, not silently decided)
--------------------------------------------------------------------------
Status vocabulary is QUEUED / RUNNING / COMPLETED / FAILED / CANCELLED, per
this mission's own literal list. Only three transitions are wired by the
five required methods below:
  enqueue()  -> QUEUED
  dequeue()  -> QUEUED  -> RUNNING
  cancel()   -> QUEUED | RUNNING -> CANCELLED

COMPLETED and FAILED are real, closed-vocabulary members (IMPORT_JOB_STATUSES
includes them, and any caller-supplied status is validated against the
full set) but no public method in this module ever transitions a job into
either one. Actually calling import_execution_engine.execute_import() and
recording whether it succeeded is a background-worker/integration concern
this mission explicitly forbids building here ("No background worker. Pure
in-memory only."): this queue tracks WHICH job should run next and lets a
caller mark it RUNNING (dequeue), never runs it. Reaching COMPLETED/FAILED
is future MWO scope, not invented here -- the same additive-vocabulary-
before-full-wiring precedent import_session.py's own "EXECUTING" status
(added by MWO-085 for a lifecycle not every caller drove yet) already set.

--------------------------------------------------------------------------
Determinism (no threading, no async, no clock, no random id)
--------------------------------------------------------------------------
job_id and queued_at are both required, caller-supplied strings -- this
module contains no uuid.uuid4()/datetime.now() call anywhere, the same
discipline import_session.py's own header note establishes for
session_id/created_at. FIFO order is NOT derived from queued_at (a caller-
supplied label this module never parses or compares) -- it is an internal
monotonic sequence counter ImportQueueManager assigns at enqueue() time,
the same role a database auto-increment id or Python's own queue.Queue
insertion order plays elsewhere; it is bookkeeping, not a fabricated
business fact, so it does not violate this Constitution's "never fabricate
data" rule. Given the same sequence of enqueue()/dequeue()/cancel() calls
twice, in two separate ImportQueueManager instances, the two managers'
list_jobs() outputs compare equal field-for-field.

Immutable DTO style reused from conflict_resolution.py/import_session.py
(frozen(slots=True) dataclasses, every plural field a tuple). Only
ImportQueueManager itself is a mutable, stateful class -- the same role
ImportSessionRepository already plays for ImportSession (in-memory dict,
no SQL, no schema, resets on restart), extended here with a monotonic
sequence counter for FIFO ordering that repository has no equivalent need
for (session lookup has no ordering requirement; job dequeue does).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

STATUS_QUEUED = "QUEUED"
STATUS_RUNNING = "RUNNING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"

IMPORT_JOB_STATUSES = (STATUS_QUEUED, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED)

# Terminal states a job can never leave once reached -- cancelling or
# re-dequeuing a job already in one of these would silently misrepresent
# what actually happened to it.
_TERMINAL_STATUSES = (STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED)


@dataclass(frozen=True, slots=True)
class ImportJob:
    """Immutable. One unit of queued import work, identified by the
    caller-supplied job_id and referencing an existing ImportSession by
    session_id only (opaque string, never resolved or inspected here).
    `sequence` is the internal FIFO ordering counter ImportQueueManager
    assigns at enqueue() time -- not a business fact, never caller-
    supplied. `reason` is populated only for a CANCELLED job (the
    caller-supplied cancellation reason, or None if none was given);
    never fabricated for any other status."""

    job_id: str
    session_id: str
    status: str
    queued_at: str
    sequence: int
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ImportQueue:
    """An immutable snapshot of the whole queue's state at the instant it
    was taken -- returned by list_jobs(), never mutated afterward (the
    live state keeps changing inside ImportQueueManager; this is a
    read-only picture of one moment). `jobs` is ordered by `sequence`
    (enqueue order), the same FIFO ordering dequeue() itself uses. Every
    count below is len()-derived from `jobs`, never a separately-tracked
    counter -- the same "summary" discipline ImportSummary/
    ImportSessionStatistics/ConflictReport already established."""

    jobs: tuple[ImportJob, ...]
    total_count: int
    queued_count: int
    running_count: int
    completed_count: int
    failed_count: int
    cancelled_count: int


def _build_queue_snapshot(jobs: list[ImportJob]) -> ImportQueue:
    ordered = tuple(sorted(jobs, key=lambda job: job.sequence))
    return ImportQueue(
        jobs=ordered,
        total_count=len(ordered),
        queued_count=sum(1 for job in ordered if job.status == STATUS_QUEUED),
        running_count=sum(1 for job in ordered if job.status == STATUS_RUNNING),
        completed_count=sum(1 for job in ordered if job.status == STATUS_COMPLETED),
        failed_count=sum(1 for job in ordered if job.status == STATUS_FAILED),
        cancelled_count=sum(1 for job in ordered if job.status == STATUS_CANCELLED),
    )


class ImportQueueManager:
    """Pure in-memory FIFO queue of ImportJob records. No threading, no
    async, no scheduler, no Redis, no background worker -- every method is
    a plain, synchronous, immediate dict operation, the same
    ImportSessionRepository (import_session_repository.py) role for
    ImportSession extended here with a monotonic sequence counter for
    ordering."""

    def __init__(self) -> None:
        self._jobs: dict[str, ImportJob] = {}
        self._sequence = 0

    def enqueue(self, job_id: str, session_id: str, queued_at: str) -> ImportJob:
        """Appends a new job to the back of the queue, status QUEUED.
        Raises ValueError if job_id already exists -- enqueue() never
        silently overwrites (the same "create() never silently overwrites"
        discipline ImportSessionRepository.create() already established)."""
        if job_id in self._jobs:
            raise ValueError(f"Import job '{job_id}' already exists")

        self._sequence += 1
        job = ImportJob(
            job_id=job_id,
            session_id=session_id,
            status=STATUS_QUEUED,
            queued_at=queued_at,
            sequence=self._sequence,
        )
        self._jobs[job_id] = job
        return job

    def dequeue(self) -> ImportJob | None:
        """Returns the next QUEUED job -- the one with the lowest
        `sequence` among jobs still QUEUED -- and transitions it to
        RUNNING. Returns None when no job is QUEUED: an honest,
        non-exceptional signal for a legitimate state (an empty, or
        fully-drained, queue), never an error."""
        queued = [job for job in self._jobs.values() if job.status == STATUS_QUEUED]
        if not queued:
            return None

        next_job = min(queued, key=lambda job: job.sequence)
        updated = replace(next_job, status=STATUS_RUNNING)
        self._jobs[next_job.job_id] = updated
        return updated

    def cancel(self, job_id: str, reason: str | None = None) -> ImportJob:
        """QUEUED or RUNNING -> CANCELLED. Raises ValueError for an
        unknown job_id, or for a job already in a terminal state
        (COMPLETED/FAILED/CANCELLED) -- cancelling a job that already
        finished would silently misrepresent what actually happened to
        it, never a silent no-op."""
        job = self._require(job_id)
        if job.status in _TERMINAL_STATUSES:
            raise ValueError(f"Import job '{job_id}' is already {job.status} and cannot be cancelled")

        updated = replace(job, status=STATUS_CANCELLED, reason=reason)
        self._jobs[job_id] = updated
        return updated

    def get_status(self, job_id: str) -> str | None:
        """Returns the job's current status, or None if job_id is
        unknown -- the same "get() returns None for a missing key" query
        discipline ImportSessionRepository.get() already established,
        never an exception for a plain lookup."""
        job = self._jobs.get(job_id)
        return job.status if job is not None else None

    def list_jobs(self) -> ImportQueue:
        """The full queue snapshot, jobs ordered by enqueue (FIFO)
        order."""
        return _build_queue_snapshot(list(self._jobs.values()))

    def _require(self, job_id: str) -> ImportJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Import job '{job_id}' does not exist")
        return job


__all__ = [
    "STATUS_QUEUED",
    "STATUS_RUNNING",
    "STATUS_COMPLETED",
    "STATUS_FAILED",
    "STATUS_CANCELLED",
    "IMPORT_JOB_STATUSES",
    "ImportJob",
    "ImportQueue",
    "ImportQueueManager",
]
