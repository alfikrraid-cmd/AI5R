from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class ActionManufacturingInput:
    recommendation_object: dict[str, Any]
    action_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ActionManufacturingStation(BaseManufacturingStation):
    station_code = "MS-011"
    station_name = "Action Manufacturing Station"
    object_type = "ACTION_OBJECT"
    event_type = "ACTION_MANUFACTURED"
    required_input = "recommendation_object"

    def manufacture(
        self,
        manufacturing_input: ActionManufacturingInput,
    ):
        if not manufacturing_input.recommendation_object:
            raise ValueError("Recommendation object is required")

        result = super().manufacture(
            payload={
                "recommendation_object": manufacturing_input.recommendation_object,
                "action_data": manufacturing_input.action_data,
            },
            metadata=manufacturing_input.metadata,
        )

        result.action_id = result.object_id
        result.action_timestamp = result.manufactured_at
        result.action_object = {
            "type": "ACTION_OBJECT",
            "action_id": result.object_id,
            "recommendation_object": manufacturing_input.recommendation_object,
            "action_data": manufacturing_input.action_data,
            "metadata": manufacturing_input.metadata,
            "action_timestamp": result.manufactured_at,
        }

        result.events[0]["action_id"] = result.object_id

        return result


ActionManufacturingResult = object
