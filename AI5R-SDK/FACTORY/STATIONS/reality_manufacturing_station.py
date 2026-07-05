from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class RealityManufacturingInput:
    source: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class RealityManufacturingStation(BaseManufacturingStation):
    station_code = "MS-001"
    station_name = "Reality Manufacturing Station"
    object_type = "REALITY_OBJECT"
    event_type = "REALITY_MANUFACTURED"
    required_input = "source"

    def manufacture(
        self,
        manufacturing_input: RealityManufacturingInput,
        context: dict[str, Any] | None = None,
    ):
        if not manufacturing_input.source:
            raise ValueError("Reality source is required")

        result = super().manufacture(
            payload={
                "source": manufacturing_input.source,
                "payload": manufacturing_input.payload,
                "context": context or {},
            },
            metadata=manufacturing_input.metadata,
        )

        result.source = manufacturing_input.source
        result.reality_object = {
            "type": "REALITY_OBJECT",
            "source": manufacturing_input.source,
            "payload": manufacturing_input.payload,
            "metadata": manufacturing_input.metadata,
            "context": context or {},
            "manufactured_at": result.manufactured_at,
        }

        result.events[0]["station"] = self.full_station_name()

        return result


RealityManufacturingResult = object
