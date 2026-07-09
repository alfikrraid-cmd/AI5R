from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class WorkforceEvent:
    event_type: str
    source: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: f"WEVT-{uuid4()}")
    created_at: str = field(default_factory=_now)


class WorkforceEventBus:
    def __init__(self) -> None:
        self._events: list[WorkforceEvent] = []

    def publish(self, event: WorkforceEvent) -> WorkforceEvent:
        self._events.append(event)
        return event

    def all(self) -> list[WorkforceEvent]:
        return list(self._events)

    def by_type(self, event_type: str) -> list[WorkforceEvent]:
        return [
            event
            for event in self._events
            if event.event_type == event_type
        ]

    def stream(self) -> list[dict[str, Any]]:
        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "source": event.source,
                "payload": event.payload,
                "created_at": event.created_at,
            }
            for event in self._events
        ]
