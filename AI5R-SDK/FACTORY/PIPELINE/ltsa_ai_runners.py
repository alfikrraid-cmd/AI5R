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


def build_ltsa_ai_runners():
    return {
        "MS-001": lambda payload: RealityManufacturingStation().manufacture(
            RealityManufacturingInput(
                source=payload["source"],
                payload=payload["payload"],
                metadata=payload.get("metadata", {}),
            ),
            context=payload.get("context", {}),
        ).reality_object,

        "MS-002": lambda payload: WarehouseManufacturingStation().manufacture(
            WarehouseManufacturingInput(reality_object=payload)
        ).warehouse_object,

        "MS-003": lambda payload: ExperienceManufacturingStation().manufacture(
            ExperienceManufacturingInput(warehouse_object=payload)
        ).experience_object,

        "MS-004": lambda payload: MemoryManufacturingStation().manufacture(
            MemoryManufacturingInput(experience_object=payload)
        ).memory_object,

        "MS-005": lambda payload: KnowledgeManufacturingStation().manufacture(
            KnowledgeManufacturingInput(memory_object=payload)
        ).knowledge_object,

        "MS-006": lambda payload: CapabilityManufacturingStation().manufacture(
            CapabilityManufacturingInput(knowledge_object=payload)
        ).capability_object,

        "MS-007": lambda payload: ContextManufacturingStation().manufacture(
            ContextManufacturingInput(
                capability_object=payload,
                context_data={"product": "LTSA-AI"},
            )
        ).context_object,

        "MS-008": lambda payload: ReasoningManufacturingStation().manufacture(
            ReasoningManufacturingInput(
                context_object=payload,
                reasoning_data={"mode": "ltsa_basic_reasoning"},
            )
        ).reasoning_object,

        "MS-009": lambda payload: DecisionManufacturingStation().manufacture(
            DecisionManufacturingInput(
                reasoning_object=payload,
                decision_data={"decision": "prepare_recommendation"},
            )
        ).decision_object,

        "MS-010": lambda payload: RecommendationManufacturingStation().manufacture(
            RecommendationManufacturingInput(
                decision_object=payload,
                recommendation_data={"recommendation": "generate_action_plan"},
            )
        ).recommendation_object,

        "MS-011": lambda payload: ActionManufacturingStation().manufacture(
            ActionManufacturingInput(
                recommendation_object=payload,
                action_data={"action": "execute_next_step"},
            )
        ).action_object,
    }
