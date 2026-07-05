from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class ContextManufacturingInput:
    capability_object: dict[str, Any]
    context_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextManufacturingStation(BaseManufacturingStation):
    station_code = "MS-007"
    station_name = "Context Manufacturing Station"
    object_type = "CONTEXT_OBJECT"
    event_type = "CONTEXT_MANUFACTURED"
    required_input = "capability_object"

    def manufacture(
        self,
        manufacturing_input: ContextManufacturingInput,
    ):
        if not manufacturing_input.capability_object:
            raise ValueError("Capability object is required")

        result = super().manufacture(
            payload={
                "capability_object": manufacturing_input.capability_object,
                "context_data": manufacturing_input.context_data,
            },
            metadata=manufacturing_input.metadata,
        )

        result.context_id = result.object_id
        result.context_timestamp = result.manufactured_at
        result.context_object = {
            "type": "CONTEXT_OBJECT",
            "context_id": result.object_id,
            "capability_object": manufacturing_input.capability_object,
            "context_data": manufacturing_input.context_data,
            "metadata": manufacturing_input.metadata,
            "context_timestamp": result.manufactured_at,
        }

        result.events[0]["context_id"] = result.object_id

        return result


ContextManufacturingResult = object
