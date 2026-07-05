from dataclasses import dataclass
from typing import Any

from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject
from INTELLIGENCE.KNOWLEDGE.RUNTIME.knowledge_runtime import KnowledgeRuntime


@dataclass
class KnowledgeAPIResponse:
    status: str
    knowledge_id: str
    data: dict[str, Any]


class KnowledgeAPI:
    def __init__(self, runtime: KnowledgeRuntime | None = None):
        self.runtime = runtime or KnowledgeRuntime()

    def process(self, payload: dict[str, Any]) -> KnowledgeAPIResponse:
        if not payload:
            raise ValueError("payload is required")

        result = self.runtime.process(payload)
        knowledge = result.knowledge_object

        return KnowledgeAPIResponse(
            status="processed",
            knowledge_id=knowledge.knowledge_id,
            data={
                "knowledge": knowledge.to_dict(),
                "stages": result.stages,
                "events": [
                    event.to_dict()
                    for event in result.events
                ],
            },
        )

    def process_many(
        self,
        payloads: list[dict[str, Any]],
    ) -> list[KnowledgeAPIResponse]:
        if not payloads:
            raise ValueError("payloads are required")

        return [
            self.process(payload)
            for payload in payloads
        ]

    def create_object(self, payload: dict[str, Any]) -> KnowledgeObject:
        if not payload:
            raise ValueError("payload is required")

        return KnowledgeObject.from_dict(payload)
