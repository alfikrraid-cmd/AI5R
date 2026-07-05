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

    def extract_knowledge(self, memory_object: dict[str, Any]) -> dict[str, Any]:
        experience_object = memory_object.get("experience_object", {})
        warehouse_object = experience_object.get("warehouse_object", {})
        reality_object = warehouse_object.get("reality_object", {})
        payload = reality_object.get("payload", {})

        observation = str(payload.get("observation", "")).lower()

        if "technical service agreement" in observation or "ltsa" in observation:
            return {
                "knowledge_type": "SERVICE_AGREEMENT_NEED",
                "pattern": "Customer Needs Technical Service Agreement Support",
                "confidence": 0.9,
                "evidence": [payload.get("observation", "")],
            }

        if "pump" in observation and ("failure" in observation or "rusak" in observation):
            return {
                "knowledge_type": "FAILURE_PATTERN",
                "pattern": "Pump Failure Pattern",
                "confidence": 0.85,
                "evidence": [payload.get("observation", "")],
            }

        return {
            "knowledge_type": "GENERAL_OBSERVATION",
            "pattern": "General Knowledge Extracted From Memory",
            "confidence": 0.5,
            "evidence": [payload.get("observation", "")],
        }

    def manufacture(
        self,
        manufacturing_input: KnowledgeManufacturingInput,
    ):
        if not manufacturing_input.memory_object:
            raise ValueError("Memory object is required")

        extracted_knowledge = self.extract_knowledge(
            manufacturing_input.memory_object
        )

        result = super().manufacture(
            payload={
                "memory_object": manufacturing_input.memory_object,
                "extracted_knowledge": extracted_knowledge,
            },
            metadata=manufacturing_input.metadata,
        )

        result.knowledge_id = result.object_id
        result.knowledge_timestamp = result.manufactured_at
        result.knowledge_object = {
            "type": "KNOWLEDGE_OBJECT",
            "knowledge_id": result.object_id,
            "memory_object": manufacturing_input.memory_object,
            "extracted_knowledge": extracted_knowledge,
            "metadata": manufacturing_input.metadata,
            "knowledge_timestamp": result.manufactured_at,
        }

        result.events[0]["knowledge_id"] = result.object_id

        return result


KnowledgeManufacturingResult = object
