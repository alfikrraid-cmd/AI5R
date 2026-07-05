from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class CapabilityManufacturingInput:
    knowledge_object: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityManufacturingStation(BaseManufacturingStation):
    station_code = "MS-006"
    station_name = "Capability Manufacturing Station"
    object_type = "CAPABILITY_OBJECT"
    event_type = "CAPABILITY_MANUFACTURED"
    required_input = "knowledge_object"

    def manufacture(
        self,
        manufacturing_input: CapabilityManufacturingInput,
    ):
        if not manufacturing_input.knowledge_object:
            raise ValueError("Knowledge object is required")

        result = super().manufacture(
            payload={
                "knowledge_object": manufacturing_input.knowledge_object,
            },
            metadata=manufacturing_input.metadata,
        )

        result.capability_id = result.object_id
        result.capability_timestamp = result.manufactured_at

        result.capability_object = {
            "type": "CAPABILITY_OBJECT",
            "capability_id": result.object_id,
            "knowledge_object": manufacturing_input.knowledge_object,
            "metadata": manufacturing_input.metadata,
            "capability_timestamp": result.manufactured_at,
        }

        result.events[0]["capability_id"] = result.object_id

        return result


CapabilityManufacturingResult = object
