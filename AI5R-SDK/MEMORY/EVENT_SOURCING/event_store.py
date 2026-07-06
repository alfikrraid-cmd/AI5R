from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class Event:
    event_id: str
    aggregate_id: str
    event_type: str
    payload: dict
    created_at: str


class EventStore:
    def __init__(self):
        self._events: dict[str, list[Event]] = {}

    def append(self, aggregate_id: str, event_type: str, payload: dict) -> Event:
        event = Event(
            event_id=str(uuid.uuid4()),
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(UTC).isoformat(),
        )

        self._events.setdefault(aggregate_id, []).append(event)
        return event

    def get(self, aggregate_id: str) -> list[Event]:
        return list(self._events.get(aggregate_id, []))

    def rebuild(self, aggregate_id: str) -> dict:
        state = {}

        for event in self._events.get(aggregate_id, []):
            state.update(event.payload)

        return state

    def snapshot(self):
        return {
            agg: [
                {
                    "event_type": e.event_type,
                    "payload": e.payload,
                }
                for e in events
            ]
            for agg, events in self._events.items()
        }
