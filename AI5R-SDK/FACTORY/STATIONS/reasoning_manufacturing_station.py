from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class ReasoningManufacturingInput:
    context_object: dict[str, Any]
    reasoning_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ReasoningManufacturingStation(BaseManufacturingStation):
    station_code = "MS-008"
    station_name = "Reasoning Manufacturing Station"
    object_type = "REASONING_OBJECT"
    event_type = "REASONING_MANUFACTURED"
    required_input = "context_object"

    def manufacture(
        self,
        manufacturing_input: ReasoningManufacturingInput,
    ):
        if not manufacturing_input.context_object:
            raise ValueError("Context object is required")

        result = super().manufacture(
            payload={
                "context_object": manufacturing_input.context_object,
                "reasoning_data": manufacturing_input.reasoning_data,
            },
            metadata=manufacturing_input.metadata,
        )

        result.reasoning_id = result.object_id
        result.reasoning_timestamp = result.manufactured_at
        result.reasoning_object = {
            "type": "REASONING_OBJECT",
            "reasoning_id": result.object_id,
            "context_object": manufacturing_input.context_object,
            "reasoning_data": manufacturing_input.reasoning_data,
            "metadata": manufacturing_input.metadata,
            "reasoning_timestamp": result.manufactured_at,
        }

        result.events[0]["reasoning_id"] = result.object_id

        return result


ReasoningManufacturingResult = object
