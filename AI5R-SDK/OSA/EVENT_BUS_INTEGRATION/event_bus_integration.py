from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class OSAEventType(str, Enum):
    PIPELINE_STARTED = "PIPELINE_STARTED"
    TASK_CREATED = "TASK_CREATED"
    CAPABILITY_RESOLVED = "CAPABILITY_RESOLVED"
    EMPLOYEE_ASSIGNED = "EMPLOYEE_ASSIGNED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    REFLECTION_CREATED = "REFLECTION_CREATED"
    MEMORY_LEARNED = "MEMORY_LEARNED"
    PIPELINE_COMPLETED = "PIPELINE_COMPLETED"


@dataclass
class OSAEvent:
    event_id: str
    event_type: OSAEventType
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class OSAEventBusIntegration:
    def __init__(self):
        self.events: list[OSAEvent] = []

    def publish(
        self,
        event_type: OSAEventType,
        source: str,
        payload: dict[str, Any] | None = None,
    ) -> OSAEvent:
        event = OSAEvent(
            event_id=f"OSA-EVT-{len(self.events) + 1:06d}",
            event_type=event_type,
            source=source,
            payload=payload or {},
        )

        self.events.append(event)
        return event

    def list_events(self) -> list[OSAEvent]:
        return list(self.events)

    def list_by_type(self, event_type: OSAEventType) -> list[OSAEvent]:
        return [
            event
            for event in self.events
            if event.event_type == event_type
        ]

    def clear(self) -> None:
        self.events.clear()
