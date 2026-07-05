from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class DecisionManufacturingInput:
    reasoning_object: dict[str, Any]
    decision_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class DecisionManufacturingStation(BaseManufacturingStation):
    station_code = "MS-009"
    station_name = "Decision Manufacturing Station"
    object_type = "DECISION_OBJECT"
    event_type = "DECISION_MANUFACTURED"
    required_input = "reasoning_object"

    def manufacture(
        self,
        manufacturing_input: DecisionManufacturingInput,
    ):
        if not manufacturing_input.reasoning_object:
            raise ValueError("Reasoning object is required")

        result = super().manufacture(
            payload={
                "reasoning_object": manufacturing_input.reasoning_object,
                "decision_data": manufacturing_input.decision_data,
            },
            metadata=manufacturing_input.metadata,
        )

        result.decision_id = result.object_id
        result.decision_timestamp = result.manufactured_at
        result.decision_object = {
            "type": "DECISION_OBJECT",
            "decision_id": result.object_id,
            "reasoning_object": manufacturing_input.reasoning_object,
            "decision_data": manufacturing_input.decision_data,
            "metadata": manufacturing_input.metadata,
            "decision_timestamp": result.manufactured_at,
        }

        result.events[0]["decision_id"] = result.object_id

        return result


DecisionManufacturingResult = object
