from __future__ import annotations

from OSA.EVENT_BUS_INTEGRATION import OSAEvent
from OSA.STUDIO_EVENT_STREAM import StudioEvent, StudioEventStream


class RuntimeEventBridge:
    def __init__(self, studio_stream: StudioEventStream | None = None):
        self.studio_stream = studio_stream or StudioEventStream()

    def publish_runtime_event(self, runtime_event: OSAEvent) -> StudioEvent:
        if runtime_event is None:
            raise ValueError("runtime_event is required")

        payload = {
            "event_id": runtime_event.event_id,
            "event_type": runtime_event.event_type.value,
            "source": runtime_event.source,
            "created_at": runtime_event.created_at,
            **runtime_event.payload,
        }

        return self.studio_stream.publish(
            event_type=runtime_event.event_type.value,
            payload=payload,
        )
