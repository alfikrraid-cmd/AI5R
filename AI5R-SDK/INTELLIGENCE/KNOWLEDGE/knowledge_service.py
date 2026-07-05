from dataclasses import dataclass
from typing import Any

from FOUNDATION.canonical_pipeline import CanonicalPipeline, PipelineStage
from FOUNDATION.canonical_runtime import CanonicalRuntime
from FOUNDATION.canonical_registry import CanonicalRegistry

from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject
from INTELLIGENCE.KNOWLEDGE.knowledge_processing_pipeline import (
    KnowledgeProcessingPipeline,
)


@dataclass
class KnowledgeServiceResult:
    knowledge_object: KnowledgeObject
    runtime_result: Any


class KnowledgeService:

    def __init__(self):
        self.registry = CanonicalRegistry()
        self.runtime = CanonicalRuntime(self.registry)
        self.processing = KnowledgeProcessingPipeline()

        pipeline = CanonicalPipeline(
            pipeline_name="Knowledge Processing Pipeline",
        )

        pipeline.add_stage(
            PipelineStage(
                stage_id="KP-001",
                name="Knowledge Processing",
                handler=self._process_stage,
            )
        )

        self.runtime.register_pipeline(
            object_type="KNOWLEDGE_OBJECT",
            pipeline=pipeline,
        )

    def process(
        self,
        knowledge: KnowledgeObject | dict[str, Any],
    ) -> KnowledgeServiceResult:

        if isinstance(knowledge, dict):
            knowledge = KnowledgeObject.from_dict(knowledge)

        runtime_result = self.runtime.run(knowledge)

        processed = KnowledgeObject.from_dict(
            runtime_result.output
        )

        return KnowledgeServiceResult(
            knowledge_object=processed,
            runtime_result=runtime_result,
        )

    def _process_stage(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.processing.execute(payload)
        return result.knowledge_object.to_dict()
