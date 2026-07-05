from dataclasses import dataclass, field
from typing import Any

from FOUNDATION.canonical_event import CanonicalEvent
from FOUNDATION.canonical_identity import CanonicalIdentityGenerator
from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject
from INTELLIGENCE.KNOWLEDGE.knowledge_processing_pipeline import (
    KnowledgeProcessingPipeline,
)


@dataclass
class KnowledgeRuntimeResult:
    runtime_id: str
    knowledge_object: KnowledgeObject
    stages: list[str]
    events: list[CanonicalEvent] = field(default_factory=list)


class KnowledgeRuntime:
    def __init__(self):
        self.runtime_id = CanonicalIdentityGenerator.generate("KRT").value
        self.pipeline = KnowledgeProcessingPipeline()
        self.events: list[CanonicalEvent] = []

    def process(
        self,
        knowledge: KnowledgeObject | dict[str, Any],
    ) -> KnowledgeRuntimeResult:
        result = self.pipeline.process(knowledge)
        knowledge_object = result.knowledge_object

        event = CanonicalEvent(
            event_id=CanonicalIdentityGenerator.generate("EVT").value,
            event_type="KNOWLEDGE_PROCESSED",
            source_object_id=knowledge_object.object_id,
            source_object_type=knowledge_object.object_type,
            payload={
                "runtime_id": self.runtime_id,
                "knowledge_id": knowledge_object.knowledge_id,
                "stages": result.stages,
                "classification": knowledge_object.classification,
                "priority": knowledge_object.priority,
            },
        )

        self.events.append(event)

        return KnowledgeRuntimeResult(
            runtime_id=self.runtime_id,
            knowledge_object=knowledge_object,
            stages=result.stages,
            events=[event],
        )

    def process_many(
        self,
        knowledge_objects: list[KnowledgeObject | dict[str, Any]],
    ) -> list[KnowledgeRuntimeResult]:
        if not knowledge_objects:
            raise ValueError("knowledge_objects are required")

        return [self.process(item) for item in knowledge_objects]

    def emitted_events(self) -> list[CanonicalEvent]:
        return self.events
