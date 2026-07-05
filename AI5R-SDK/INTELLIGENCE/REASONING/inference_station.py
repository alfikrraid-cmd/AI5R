from dataclasses import dataclass, field
from typing import Any

from INTELLIGENCE.REASONING.reasoning_object import ReasoningObject
from INTELLIGENCE.REASONING.CONTRACTS.reasoning_contract import ReasoningStationInput


@dataclass
class InferenceManufacturingResult:
    inference_objects: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


class InferenceManufacturingStation:
    station_code = "RS-004"
    station_name = "Inference Manufacturing Station"

    def process(
        self,
        station_input: ReasoningStationInput,
    ) -> InferenceManufacturingResult:
        reasoning_object = station_input.reasoning_object
        context = station_input.context or {}

        premises = context.get("premises")

        if not premises:
            raise ValueError("premises are required")

        inference_objects = []

        for index, premise in enumerate(premises, start=1):
            inference_id = premise.get("premise_id", f"INF-RS004-{index}")

            inference_object = {
                "inference_id": inference_id,
                "source_premise": premise,
                "conclusion": premise.get("claim") or premise.get("summary"),
                "confidence": premise.get("confidence", "MEDIUM"),
            }

            inference_objects.append(inference_object)

            reasoning_object.add_reasoning_step(
                f"inference manufactured from premise {inference_id}"
            )

            if hasattr(reasoning_object, "add_supporting_knowledge"):
                knowledge_id = premise.get("knowledge_id")
                if knowledge_id:
                    reasoning_object.add_supporting_knowledge(knowledge_id)
            else:
                knowledge_id = premise.get("knowledge_id")
                if knowledge_id and knowledge_id not in reasoning_object.supporting_knowledge:
                    reasoning_object.supporting_knowledge.append(knowledge_id)

        reasoning_object.reasoning_type = "INFERENCE_MANUFACTURED"

        return InferenceManufacturingResult(
            inference_objects=inference_objects,
            metadata={
                "station_code": self.station_code,
                "station_name": self.station_name,
                "inference_count": len(inference_objects),
            },
        )
