"""MWO-LTSA-STOCK-RESPONSE-STANDARD-001 -- a minimal, process-local,
time-bounded "last resolved equipment per WhatsApp sender" cache, so a
follow-up question with no equipment named in it ("Cek stock seal yang
tersedia") can resolve to the equipment named in an earlier message in the
same conversation ("Bagaimana kondisi 211p13ar?").

Deliberately in-memory, not a new DB table/repository: the LTSA-AI read
query path is READ-ONLY by construction (see whatsapp_intake_service.py's
own _handle_ltsa_ai_query docstring -- "no pending row is created for a
query, a question can never leave state behind") and this MWO does not
reopen that invariant for every question. This cache is a best-effort UX
convenience with an explicit, disclosed limitation: it does not survive a
process restart and is not shared across multiple API worker processes.
Never treated as authoritative -- a cache miss/expiry always degrades to
asking the user which pump, never to guessing.

Entries expire after CONTEXT_TTL_SECONDS so a context resolved minutes/
hours ago is never silently reused for an unrelated later question -- "a
valid active equipment context" per this MWO's own wording implies
recency, not an unbounded memory.
"""

from __future__ import annotations

import time

# No canonical source specifies a context lifetime for a WhatsApp
# conversation; 15 minutes is a disclosed, adjustable default -- long
# enough for a natural back-and-forth ("kondisi X?" then "cek stock"),
# short enough that a context from an earlier, unrelated conversation is
# never carried into a new one.
CONTEXT_TTL_SECONDS = 15 * 60


class AssetContextCache:
    """One (tag, resolved_at) entry per sender_user_id. Not thread-safe
    beyond CPython's own GIL-protected dict operations (matches every
    other in-process singleton in this codebase -- no lock introduced)."""

    def __init__(self, ttl_seconds: int = CONTEXT_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, tuple[str, float]] = {}

    def remember(self, sender_user_id: str, tag: str) -> None:
        self._entries[sender_user_id] = (tag, time.monotonic())

    def recall(self, sender_user_id: str) -> str | None:
        entry = self._entries.get(sender_user_id)
        if entry is None:
            return None
        tag, resolved_at = entry
        if time.monotonic() - resolved_at > self._ttl_seconds:
            del self._entries[sender_user_id]
            return None
        return tag


__all__ = ["AssetContextCache", "CONTEXT_TTL_SECONDS"]
