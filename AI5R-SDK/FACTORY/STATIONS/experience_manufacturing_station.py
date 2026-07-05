from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class ExperienceManufacturingInput:
    warehouse_object: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class ExperienceManufacturingStation(BaseManufacturingStation):
    station_code = "MS-003"
    station_name = "Experience Manufacturing Station"
    object_type = "EXPERIENCE_OBJECT"
    event_type = "EXPERIENCE_MANUFACTURED"
    required_input = "warehouse_object"

    def manufacture(
        self,
        manufacturing_input: ExperienceManufacturingInput,
    ):
        if not manufacturing_input.warehouse_object:
            raise ValueError("Warehouse object is required")

        result = super().manufacture(
            payload={
                "warehouse_object": manufacturing_input.warehouse_object,
            },
            metadata=manufacturing_input.metadata,
        )

        result.experience_id = result.object_id
        result.experience_timestamp = result.manufactured_at
        result.experience_object = {
            "type": "EXPERIENCE_OBJECT",
            "experience_id": result.object_id,
            "warehouse_object": manufacturing_input.warehouse_object,
            "metadata": manufacturing_input.metadata,
            "experience_timestamp": result.manufactured_at,
        }

        result.events[0]["experience_id"] = result.object_id

        return result


ExperienceManufacturingResult = object
