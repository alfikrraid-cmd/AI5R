from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeRelationship:
    source_id: str
    target_id: str
    relationship: str
    confidence: float
    signals: list[str] = field(default_factory=list)


class KnowledgeRelationshipEngine:
    SUPPORT_WORDS = ["support", "supports", "enable", "enables", "improve", "increase"]
    CONTRADICT_WORDS = ["contradict", "conflict", "but", "however", "risk", "problem"]
    DEPEND_WORDS = ["depend", "requires", "need", "needs", "prerequisite"]
    CAUSE_WORDS = ["cause", "causes", "because", "therefore", "leads to"]
    IMPLEMENT_WORDS = ["build", "create", "implement", "deploy", "execute"]
    EXTEND_WORDS = ["extend", "expand", "scale", "enhance"]

    def analyze_pair(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> KnowledgeRelationship:
        if not source or not target:
            raise ValueError("Source and target knowledge are required")

        source_id = str(source.get("knowledge_id") or source.get("id") or "UNKNOWN_SOURCE")
        target_id = str(target.get("knowledge_id") or target.get("id") or "UNKNOWN_TARGET")

        combined_text = f"{self._collect_text(source)} {self._collect_text(target)}".lower()

        relationship, signals = self._detect_relationship(combined_text)

        return KnowledgeRelationship(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            confidence=self._confidence(signals),
            signals=signals,
        )

    def build_relationships(
        self,
        knowledge_objects: list[dict[str, Any]],
    ) -> list[KnowledgeRelationship]:
        if not knowledge_objects:
            raise ValueError("Knowledge objects are required")

        relationships: list[KnowledgeRelationship] = []

        for i, source in enumerate(knowledge_objects):
            for target in knowledge_objects[i + 1:]:
                relationships.append(self.analyze_pair(source, target))

        return relationships

    def enrich_graph(
        self,
        knowledge_objects: list[dict[str, Any]],
    ) -> dict[str, Any]:
        relationships = self.build_relationships(knowledge_objects)

        return {
            "nodes": knowledge_objects,
            "edges": [
                {
                    "source_id": item.source_id,
                    "target_id": item.target_id,
                    "relationship": item.relationship,
                    "confidence": item.confidence,
                    "signals": item.signals,
                }
                for item in relationships
            ],
        }

    def _detect_relationship(self, text: str) -> tuple[str, list[str]]:
        rule_map = {
            "CONTRADICTS": self.CONTRADICT_WORDS,
            "DEPENDS_ON": self.DEPEND_WORDS,
            "CAUSES": self.CAUSE_WORDS,
            "IMPLEMENTS": self.IMPLEMENT_WORDS,
            "EXTENDS": self.EXTEND_WORDS,
            "SUPPORTS": self.SUPPORT_WORDS,
        }

        best_relationship = "RELATED_TO"
        best_signals: list[str] = []

        for relationship, words in rule_map.items():
            signals = [word for word in words if word in text]
            if len(signals) > len(best_signals):
                best_relationship = relationship
                best_signals = signals

        return best_relationship, best_signals

    def _confidence(self, signals: list[str]) -> float:
        if not signals:
            return 0.35
        if len(signals) == 1:
            return 0.55
        if len(signals) == 2:
            return 0.75
        return 0.9

    def _collect_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(self._collect_text(v) for v in value.values())
        if isinstance(value, list):
            return " ".join(self._collect_text(v) for v in value)
        return str(value)
