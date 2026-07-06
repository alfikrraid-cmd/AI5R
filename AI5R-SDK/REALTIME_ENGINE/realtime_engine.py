from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


@dataclass
class RealtimeEvent:
    event_type: str
    payload: dict[str, Any]
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class RealtimeEngine:

    def __init__(self):
        self.events = []

    def ingest(self, event: RealtimeEvent):
        self.events.append(event)

        return {
            "status": "RECEIVED",
            "event_type": event.event_type,
            "timestamp": event.created_at
        }

    def observe(self):
        return {
            "total_events": len(self.events),
            "latest_event": (
                self.events[-1].event_type
                if self.events
                else None
            )
        }

    def process(self, event: RealtimeEvent):

        observation = {
            "type": "OBSERVATION",
            "source": event.event_type,
            "data": event.payload
        }

        return observation
