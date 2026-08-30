"""MWO-LTSA-FLEET-ATTENTION-001 -- prevents a duplicate acknowledgement +
duplicate final answer when Meta's webhook retries the SAME inbound
message (provider_message_id) because our own first attempt at answering
a slow "which pumps need attention" query did not respond before Meta's
own delivery timeout.

Process-local, in-memory, TTL-bound -- the exact same disclosed trade-off
as whatsapp_asset_context.py's own AssetContextCache (does not survive a
process restart, not shared across multiple API worker processes; this
MWO does not reopen the LTSA-AI-query path's "read-only, no DB row" design
to solve this more durably -- see that module's own header for the full
reasoning). A cache miss always means "treat as a fresh delivery", never
"assume duplicate" -- this guards against sending a second message, never
against answering a genuinely new question.
"""

from __future__ import annotations

import time

# Long enough to cover a realistic sequence of webhook retries for one
# slow query (Meta's own retry window), short enough that a
# provider_message_id is never remembered indefinitely.
DELIVERY_TTL_SECONDS = 10 * 60


class FleetQueryDeliveryTracker:
    def __init__(self, ttl_seconds: int = DELIVERY_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._seen: dict[str, float] = {}

    def _key(self, sender_user_id: str, provider_message_id: str) -> str:
        return f"{sender_user_id}:{provider_message_id}"

    def is_duplicate(self, sender_user_id: str, provider_message_id: str) -> bool:
        key = self._key(sender_user_id, provider_message_id)
        seen_at = self._seen.get(key)
        if seen_at is None:
            return False
        if time.monotonic() - seen_at > self._ttl_seconds:
            del self._seen[key]
            return False
        return True

    def mark_seen(self, sender_user_id: str, provider_message_id: str) -> None:
        self._seen[self._key(sender_user_id, provider_message_id)] = time.monotonic()


__all__ = ["FleetQueryDeliveryTracker", "DELIVERY_TTL_SECONDS"]
