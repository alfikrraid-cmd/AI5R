from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Iterable

from OSA.STUDIO_EVENT_STREAM import StudioEvent, StudioEventStream


class LiveStreamAPI:
    def __init__(self, event_stream: StudioEventStream | None = None):
        self.event_stream = event_stream or StudioEventStream()

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> StudioEvent:
        return self.event_stream.publish(
            event_type=event_type,
            payload=payload,
        )

    def latest(self, limit: int = 50) -> dict[str, Any]:
        events = self.event_stream.latest(limit)

        return {
            "type": "AI5R_STUDIO_EVENT_STREAM",
            "version": "1.0",
            "count": len(events),
            "events": [
                asdict(event)
                for event in events
            ],
        }

    def sse(self, limit: int = 50) -> Iterable[str]:
        for event in self.event_stream.latest(limit):
            yield self._to_sse(event)

    def _to_sse(self, event: StudioEvent) -> str:
        return (
            f"event: {event.event_type}\n"
            f"data: {json.dumps(asdict(event))}\n\n"
        )
