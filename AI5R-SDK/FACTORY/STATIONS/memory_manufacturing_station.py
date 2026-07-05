from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class MemoryManufacturingInput:
    experience_object: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryManufacturingResult:
    status: str
    station: str
    memory_object: dict[str, Any]
    memory_id: str
    memory_timestamp: str
    events: list[dict[str, Any]]


class MemoryManufacturingStation:
    station_name = "MS-004 Memory Manufacturing Station"

    def manufacture(
        self,
        manufacturing_input: MemoryManufacturingInput,
    ) -> MemoryManufacturingResult:
        if not manufacturing_input.experience_object:
            raise ValueError("Experience object is required")

        memory_timestamp = datetime.now(timezone.utc).isoformat()
        memory_id = str(uuid4())

        memory_object = {
            "type": "MEMORY_OBJECT",
            "memory_id": memory_id,
            "experience_object": manufacturing_input.experience_object,
            "metadata": manufacturing_input.metadata,
            "memory_timestamp": memory_timestamp,
        }

        events = [
            {
                "event_type": "MEMORY_MANUFACTURED",
                "station": self.station_name,
                "memory_id": memory_id,
                "created_at": memory_timestamp,
            }
        ]

        return MemoryManufacturingResult(
            status="MANUFACTURED",
            station=self.station_name,
            memory_object=memory_object,
            memory_id=memory_id,
            memory_timestamp=memory_timestamp,
            events=events,
        )
