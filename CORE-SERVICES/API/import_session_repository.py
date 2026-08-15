"""
Import API Foundation -- ImportSessionRepository: in-memory storage only,
added because GET /api/ltsa/import/status/{session_id} cannot return "the
current ImportSession" without something to read it back from after
POST /api/ltsa/import/session created it. No SQL, no schema, no gateway --
process-memory only, resetting on restart, exactly matching this mission's
own "No persistence required if repository does not yet exist" allowance.

Storage only, not business logic: every method below does no validation,
no derivation, no decision-making of any kind -- they hold and return
whole ImportSession instances exactly as build_import_session()/
advance_import_session() (import_session.py, MWO-LTSA-077/085, reused
unmodified) already built them.

--------------------------------------------------------------------------
MWO-LTSA-085 -- full CRUD (this revision)
--------------------------------------------------------------------------
Previously save()/get() only. Extended, additively, with update()/
delete()/list_sessions() -- "Repository must support create, update, get,
delete, list. No database. Memory only." `create()` is `save()` renamed
for a clearer, symmetric verb pairing with `update()` (both still do the
exact same single dict-assignment; `save` is kept as a backward-compatible
alias so CORE-SERVICES/BACKEND-API/routers/import_router.py's existing
`import_session_repository.save(session)` call keeps working unchanged --
this MWO does not touch that router).

Dependency-injected the same way every existing Gateway in dependencies.py
already is: one singleton instance, one zero-arg provider function -- no
router in this codebase constructs a stateful object inline, and this one
doesn't either.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from import_session import ImportSession


class ImportSessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, "ImportSession"] = {}

    def create(self, session: "ImportSession") -> "ImportSession":
        """Stores a new session. Raises ValueError if a session with the
        same session_id already exists -- create() never silently
        overwrites (that is update()'s job)."""
        if session.session_id in self._sessions:
            raise ValueError(f"Import session '{session.session_id}' already exists")
        self._sessions[session.session_id] = session
        return session

    def save(self, session: "ImportSession") -> None:
        """Backward-compatible alias for create-or-replace, unchanged
        behavior from the pre-MWO-LTSA-085 shape -- import_router.py's
        existing POST .../session handler calls this exact method."""
        self._sessions[session.session_id] = session

    def update(self, session: "ImportSession") -> "ImportSession":
        """Replaces an existing session (same session_id) with the new,
        already-built ImportSession the caller supplies -- typically the
        result of import_session.advance_import_session(). Raises
        ValueError if no session with that id exists yet (use create()
        for a genuinely new session)."""
        if session.session_id not in self._sessions:
            raise ValueError(f"Import session '{session.session_id}' does not exist")
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> "ImportSession | None":
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Returns True if a session was actually removed, False if no
        such session existed -- an honest signal, never silently a no-op
        indistinguishable from a real deletion."""
        return self._sessions.pop(session_id, None) is not None

    def list_sessions(self) -> tuple["ImportSession", ...]:
        """All sessions currently held, in insertion order (dict
        insertion order, guaranteed since Python 3.7) -- a real,
        deterministic ordering, never re-sorted or filtered."""
        return tuple(self._sessions.values())


__all__ = ["ImportSessionRepository"]
