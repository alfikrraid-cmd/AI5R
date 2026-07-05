from dataclasses import dataclass
from typing import Any

from INTELLIGENCE.KNOWLEDGE.knowledge_classifier import KnowledgeClassificationEngine
from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject
from INTELLIGENCE.KNOWLEDGE.knowledge_prioritizer import KnowledgePrioritizationEngine


@dataclass
class KnowledgeProcessingResult:
    knowledge_object: KnowledgeObject
    stages: list[str]


class KnowledgeProcessingPipeline:
    def __init__(self):
        self.classifier = KnowledgeClassificationEngine()
        self.prioritizer = KnowledgePrioritizationEngine()

    def process(
        self,
        knowledge: KnowledgeObject | dict[str, Any],
    ) -> KnowledgeProcessingResult:
        knowledge_object = self._ensure_object(knowledge)

        classification = self.classifier.classify(
            knowledge_object.to_dict()
        )

        knowledge_object.attach_classification({
            "domain": classification.domain,
            "category": classification.category,
            "confidence": classification.confidence,
            "signals": classification.signals,
        })

        priority = self.prioritizer.prioritize(
            knowledge_object.to_dict()
        )

        knowledge_object.attach_priority({
            "impact": priority.impact,
            "urgency": priority.urgency,
            "confidence": priority.confidence,
            "actionability": priority.actionability,
            "priority_score": priority.priority_score,
            "priority_level": priority.priority_level,
        })

        return KnowledgeProcessingResult(
            knowledge_object=knowledge_object,
            stages=[
                "classification",
                "prioritization",
            ],
        )

    def process_many(
        self,
        knowledge_objects: list[KnowledgeObject | dict[str, Any]],
    ) -> list[KnowledgeProcessingResult]:
        if not knowledge_objects:
            raise ValueError("knowledge_objects are required")

        return [
            self.process(item)
            for item in knowledge_objects
        ]

    def _ensure_object(
        self,
        knowledge: KnowledgeObject | dict[str, Any],
    ) -> KnowledgeObject:
        if isinstance(knowledge, KnowledgeObject):
            return knowledge

        if isinstance(knowledge, dict):
            return KnowledgeObject.from_dict(knowledge)

        raise TypeError("knowledge must be KnowledgeObject or dict")
