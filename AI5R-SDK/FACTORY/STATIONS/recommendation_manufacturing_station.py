from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class RecommendationManufacturingInput:
    decision_object: dict[str, Any]
    recommendation_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class RecommendationManufacturingStation(BaseManufacturingStation):
    station_code = "MS-010"
    station_name = "Recommendation Manufacturing Station"
    object_type = "RECOMMENDATION_OBJECT"
    event_type = "RECOMMENDATION_MANUFACTURED"
    required_input = "decision_object"

    def manufacture(
        self,
        manufacturing_input: RecommendationManufacturingInput,
    ):
        if not manufacturing_input.decision_object:
            raise ValueError("Decision object is required")

        result = super().manufacture(
            payload={
                "decision_object": manufacturing_input.decision_object,
                "recommendation_data": manufacturing_input.recommendation_data,
            },
            metadata=manufacturing_input.metadata,
        )

        result.recommendation_id = result.object_id
        result.recommendation_timestamp = result.manufactured_at
        result.recommendation_object = {
            "type": "RECOMMENDATION_OBJECT",
            "recommendation_id": result.object_id,
            "decision_object": manufacturing_input.decision_object,
            "recommendation_data": manufacturing_input.recommendation_data,
            "metadata": manufacturing_input.metadata,
            "recommendation_timestamp": result.manufactured_at,
        }

        result.events[0]["recommendation_id"] = result.object_id

        return result


RecommendationManufacturingResult = object
