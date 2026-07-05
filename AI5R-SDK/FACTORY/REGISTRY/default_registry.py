from .station_registry import StationDefinition, StationRegistry


def build_default_station_registry() -> StationRegistry:
    registry = StationRegistry()

    stations = [
        StationDefinition("MS-001", "Reality Manufacturing Station", "RealityInput", "RealityObject", "REALITY_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-002", "Warehouse Manufacturing Station", "RealityObject", "WarehouseObject", "WAREHOUSE_OBJECT_STORED", "1.0", "AI5R Factory"),
        StationDefinition("MS-003", "Experience Manufacturing Station", "WarehouseObject", "ExperienceObject", "EXPERIENCE_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-004", "Memory Manufacturing Station", "ExperienceObject", "MemoryObject", "MEMORY_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-005", "Knowledge Manufacturing Station", "MemoryObject", "KnowledgeObject", "KNOWLEDGE_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-006", "Capability Manufacturing Station", "KnowledgeObject", "CapabilityObject", "CAPABILITY_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-007", "Context Manufacturing Station", "CapabilityObject", "ContextObject", "CONTEXT_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-008", "Reasoning Manufacturing Station", "ContextObject", "ReasoningObject", "REASONING_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-009", "Decision Manufacturing Station", "ReasoningObject", "DecisionObject", "DECISION_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-010", "Recommendation Manufacturing Station", "DecisionObject", "RecommendationObject", "RECOMMENDATION_MANUFACTURED", "1.0", "AI5R Factory"),
        StationDefinition("MS-011", "Action Manufacturing Station", "RecommendationObject", "ActionObject", "ACTION_MANUFACTURED", "1.0", "AI5R Factory"),
    ]

    for station in stations:
        registry.register(station)

    return registry
