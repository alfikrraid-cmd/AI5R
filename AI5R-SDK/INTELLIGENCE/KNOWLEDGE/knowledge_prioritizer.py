from dataclasses import dataclass
from typing import Any


@dataclass
class KnowledgePriority:
    impact: float
    urgency: float
    confidence: float
    actionability: float
    priority_score: float
    priority_level: str


class KnowledgePrioritizationEngine:

    def prioritize(self, knowledge: dict[str, Any]) -> KnowledgePriority:
        if not knowledge:
            raise ValueError("Knowledge object is required")

        classification = knowledge.get("classification", {})

        confidence = float(classification.get("confidence", 0.5))

        impact = float(knowledge.get("impact", 0.5))
        urgency = float(knowledge.get("urgency", 0.5))
        actionability = float(knowledge.get("actionability", 0.5))

        score = round(
            (
                impact +
                urgency +
                confidence +
                actionability
            ) / 4,
            3,
        )

        if score >= 0.85:
            level = "CRITICAL"
        elif score >= 0.70:
            level = "HIGH"
        elif score >= 0.50:
            level = "MEDIUM"
        else:
            level = "LOW"

        return KnowledgePriority(
            impact=impact,
            urgency=urgency,
            confidence=confidence,
            actionability=actionability,
            priority_score=score,
            priority_level=level,
        )

    def enrich(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        priority = self.prioritize(knowledge)

        enriched = dict(knowledge)

        enriched["priority"] = {
            "impact": priority.impact,
            "urgency": priority.urgency,
            "confidence": priority.confidence,
            "actionability": priority.actionability,
            "priority_score": priority.priority_score,
            "priority_level": priority.priority_level,
        }

        return enriched
