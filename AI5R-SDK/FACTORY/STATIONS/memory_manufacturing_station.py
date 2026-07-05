from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class MemoryManufacturingInput:
    experience_object: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryManufacturingStation(BaseManufacturingStation):
    station_code = "MS-004"
    station_name = "Memory Manufacturing Station"
    object_type = "MEMORY_OBJECT"
    event_type = "MEMORY_MANUFACTURED"
    required_input = "experience_object"

    def manufacture(
        self,
        manufacturing_input: MemoryManufacturingInput,
    ):
        if not manufacturing_input.experience_object:
            raise ValueError("Experience object is required")

        result = super().manufacture(
            payload={
                "experience_object": manufacturing_input.experience_object,
            },
            metadata=manufacturing_input.metadata,
        )

        result.memory_id = result.object_id
        result.memory_timestamp = result.manufactured_at
        result.memory_object = {
            "type": "MEMORY_OBJECT",
            "memory_id": result.object_id,
            "experience_object": manufacturing_input.experience_object,
            "metadata": manufacturing_input.metadata,
            "memory_timestamp": result.manufactured_at,
        }

        result.events[0]["memory_id"] = result.object_id

        return result


MemoryManufacturingResult = object
