from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class StudioEvent:
    event_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class StudioEventStream:
    def __init__(self, max_events: int = 1000):
        self._events: deque[StudioEvent] = deque(maxlen=max_events)

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> StudioEvent:

        if not event_type:
            raise ValueError("event_type is required")

        event = StudioEvent(
            event_id=f"EVT-{len(self._events)+1:06d}",
            event_type=event_type,
            payload=payload,
        )

        self._events.append(event)

        return event

    def latest(self, limit: int = 50) -> list[StudioEvent]:
        return list(self._events)[-limit:]

    def size(self) -> int:
        return len(self._events)

    def clear(self):
        self._events.clear()
