from typing import Any

from INTELLIGENCE.REASONING.CONTRACTS.reasoning_contract import (
    ReasoningStationContract,
    ReasoningStationInput,
    ReasoningStationOutput,
)


class PremiseManufacturingStation(ReasoningStationContract):
    station_code = "RS-001"
    station_name = "Premise Manufacturing Station"

    def process(
        self,
        station_input: ReasoningStationInput,
    ) -> ReasoningStationOutput:
        self.validate_input(station_input)

        reasoning_object = station_input.reasoning_object
        knowledge_objects = station_input.context.get("knowledge_objects", [])

        if not knowledge_objects:
            raise ValueError("knowledge_objects are required")

        for knowledge in knowledge_objects:
            premise = self._build_premise(knowledge)
            reasoning_object.add_premise(premise)
            reasoning_object.add_supporting_knowledge(
                premise["knowledge_id"]
            )

        reasoning_object.add_reasoning_step(
            "premises manufactured from knowledge objects"
        )

        return ReasoningStationOutput(
            reasoning_object=reasoning_object,
            station_code=self.station_code,
            status="processed",
            metadata={
                "station": self.station_name,
                "premise_count": len(reasoning_object.premises),
            },
        )

    def _build_premise(self, knowledge: Any) -> dict[str, Any]:
        if hasattr(knowledge, "to_dict"):
            data = knowledge.to_dict()
        elif isinstance(knowledge, dict):
            data = knowledge
        else:
            raise TypeError("knowledge must be KnowledgeObject or dict")

        knowledge_id = data.get("knowledge_id") or data.get("object_id")
        summary = data.get("summary")

        if not knowledge_id:
            raise ValueError("knowledge_id is required")
        if not summary:
            raise ValueError("summary is required")

        return {
            "knowledge_id": knowledge_id,
            "statement": summary,
            "classification": data.get("classification", {}),
            "priority": data.get("priority", {}),
            "confidence": data.get("classification", {}).get(
                "confidence",
                0.5,
            ),
        }
