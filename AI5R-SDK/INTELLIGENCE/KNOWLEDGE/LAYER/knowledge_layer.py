from dataclasses import dataclass, field


@dataclass(frozen=True)
class LayerComponent:
    name: str
    category: str
    version: str = "1.0"


class KnowledgeLayer:

    VERSION = "1.0.0"

    OBJECTS = [
        LayerComponent(
            name="KnowledgeObject",
            category="object",
        ),
    ]

    SERVICES = [
        LayerComponent(
            name="KnowledgeService",
            category="service",
        ),
    ]

    PIPELINES = [
        LayerComponent(
            name="KnowledgeProcessingPipeline",
            category="pipeline",
        ),
    ]

    ENGINES = [
        LayerComponent(
            name="KnowledgeClassificationEngine",
            category="engine",
        ),
        LayerComponent(
            name="KnowledgePrioritizationEngine",
            category="engine",
        ),
        LayerComponent(
            name="KnowledgeRelationshipEngine",
            category="engine",
        ),
        LayerComponent(
            name="KnowledgeConflictDetectionEngine",
            category="engine",
        ),
    ]

    CAPABILITIES = [
        "classification",
        "prioritization",
        "relationship",
        "conflict_detection",
        "processing",
        "service_runtime",
    ]

    @classmethod
    def manifest(cls) -> dict:

        return {
            "layer": "Knowledge",
            "version": cls.VERSION,
            "objects": [x.name for x in cls.OBJECTS],
            "services": [x.name for x in cls.SERVICES],
            "pipelines": [x.name for x in cls.PIPELINES],
            "engines": [x.name for x in cls.ENGINES],
            "capabilities": cls.CAPABILITIES,
        }

    @classmethod
    def component_count(cls) -> int:
        return (
            len(cls.OBJECTS)
            + len(cls.SERVICES)
            + len(cls.PIPELINES)
            + len(cls.ENGINES)
        )

    @classmethod
    def supports(cls, capability: str) -> bool:
        return capability in cls.CAPABILITIES
