from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class KnowledgeManufacturingInput:
    memory_object: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeManufacturingStation(BaseManufacturingStation):
    station_code = "MS-005"
    station_name = "Knowledge Manufacturing Station"
    object_type = "KNOWLEDGE_OBJECT"
    event_type = "KNOWLEDGE_MANUFACTURED"
    required_input = "memory_object"

    def manufacture(
        self,
        manufacturing_input: KnowledgeManufacturingInput,
    ):
        if not manufacturing_input.memory_object:
            raise ValueError("Memory object is required")

        result = super().manufacture(
            payload={
                "memory_object": manufacturing_input.memory_object,
            },
            metadata=manufacturing_input.metadata,
        )

        result.knowledge_id = result.object_id
        result.knowledge_timestamp = result.manufactured_at
        result.knowledge_object = {
            "type": "KNOWLEDGE_OBJECT",
            "knowledge_id": result.object_id,
            "memory_object": manufacturing_input.memory_object,
            "metadata": manufacturing_input.metadata,
            "knowledge_timestamp": result.manufactured_at,
        }

        result.events[0]["knowledge_id"] = result.object_id

        return result


KnowledgeManufacturingResult = object
