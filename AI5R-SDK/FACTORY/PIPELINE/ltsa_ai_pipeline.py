from typing import Any

from FACTORY.PIPELINE import PipelineOrchestrator, PipelineStep
from FACTORY.STATIONS import (
    RealityManufacturingInput,
    RealityManufacturingStation,
    WarehouseManufacturingInput,
    WarehouseManufacturingStation,
    ExperienceManufacturingInput,
    ExperienceManufacturingStation,
    MemoryManufacturingInput,
    MemoryManufacturingStation,
    KnowledgeManufacturingInput,
    KnowledgeManufacturingStation,
    CapabilityManufacturingInput,
    CapabilityManufacturingStation,
    ContextManufacturingInput,
    ContextManufacturingStation,
    ReasoningManufacturingInput,
    ReasoningManufacturingStation,
    DecisionManufacturingInput,
    DecisionManufacturingStation,
    RecommendationManufacturingInput,
    RecommendationManufacturingStation,
    ActionManufacturingInput,
    ActionManufacturingStation,
)


def build_ltsa_ai_pipeline() -> PipelineOrchestrator:
    pipeline = PipelineOrchestrator()

    pipeline.add_step(
        PipelineStep(
            name="reality",
            runner=lambda payload: RealityManufacturingStation().manufacture(
                RealityManufacturingInput(
                    source=payload["source"],
                    payload=payload["payload"],
                    metadata=payload.get("metadata", {}),
                ),
                context=payload.get("context", {}),
            ).reality_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="warehouse",
            runner=lambda payload: WarehouseManufacturingStation().manufacture(
                WarehouseManufacturingInput(reality_object=payload)
            ).warehouse_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="experience",
            runner=lambda payload: ExperienceManufacturingStation().manufacture(
                ExperienceManufacturingInput(warehouse_object=payload)
            ).experience_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="memory",
            runner=lambda payload: MemoryManufacturingStation().manufacture(
                MemoryManufacturingInput(experience_object=payload)
            ).memory_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="knowledge",
            runner=lambda payload: KnowledgeManufacturingStation().manufacture(
                KnowledgeManufacturingInput(memory_object=payload)
            ).knowledge_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="capability",
            runner=lambda payload: CapabilityManufacturingStation().manufacture(
                CapabilityManufacturingInput(knowledge_object=payload)
            ).capability_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="context",
            runner=lambda payload: ContextManufacturingStation().manufacture(
                ContextManufacturingInput(
                    capability_object=payload,
                    context_data={"product": "LTSA-AI"},
                )
            ).context_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="reasoning",
            runner=lambda payload: ReasoningManufacturingStation().manufacture(
                ReasoningManufacturingInput(
                    context_object=payload,
                    reasoning_data={"mode": "ltsea_basic_reasoning"},
                )
            ).reasoning_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="decision",
            runner=lambda payload: DecisionManufacturingStation().manufacture(
                DecisionManufacturingInput(
                    reasoning_object=payload,
                    decision_data={"decision": "prepare_recommendation"},
                )
            ).decision_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="recommendation",
            runner=lambda payload: RecommendationManufacturingStation().manufacture(
                RecommendationManufacturingInput(
                    decision_object=payload,
                    recommendation_data={"recommendation": "generate_action_plan"},
                )
            ).recommendation_object,
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="action",
            runner=lambda payload: ActionManufacturingStation().manufacture(
                ActionManufacturingInput(
                    recommendation_object=payload,
                    action_data={"action": "execute_next_step"},
                )
            ).action_object,
        )
    )

    return pipeline
