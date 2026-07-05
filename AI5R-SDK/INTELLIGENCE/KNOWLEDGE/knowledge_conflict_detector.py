from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeConflict:
    knowledge_a: str
    knowledge_b: str
    conflict_type: str
    severity: str
    confidence: float
    reason: str
    signals: list[str] = field(default_factory=list)


class KnowledgeConflictDetectionEngine:
    CONFLICT_PAIRS = [
        ("online", "offline", "CHANNEL_CONFLICT"),
        ("manual", "automatic", "OPERATION_CONFLICT"),
        ("increase", "reduce", "DIRECTION_CONFLICT"),
        ("expand", "limit", "STRATEGY_CONFLICT"),
        ("premium", "cheap", "POSITIONING_CONFLICT"),
        ("fast", "slow", "EXECUTION_CONFLICT"),
        ("centralized", "decentralized", "ARCHITECTURE_CONFLICT"),
    ]

    NEGATION_WORDS = [
        "not",
        "never",
        "avoid",
        "stop",
        "reject",
        "without",
        "jangan",
        "tidak",
        "hindari",
    ]

    def detect_pair(
        self,
        knowledge_a: dict[str, Any],
        knowledge_b: dict[str, Any],
    ) -> KnowledgeConflict | None:
        if not knowledge_a or not knowledge_b:
            raise ValueError("Two knowledge objects are required")

        id_a = str(knowledge_a.get("knowledge_id") or knowledge_a.get("id") or "UNKNOWN_A")
        id_b = str(knowledge_b.get("knowledge_id") or knowledge_b.get("id") or "UNKNOWN_B")

        text_a = self._collect_text(knowledge_a).lower()
        text_b = self._collect_text(knowledge_b).lower()

        pair_conflict = self._detect_pair_conflict(text_a, text_b)
        negation_conflict = self._detect_negation_conflict(text_a, text_b)

        conflict = pair_conflict or negation_conflict

        if conflict is None:
            return None

        conflict_type, signals = conflict
        confidence = self._confidence(signals)
        severity = self._severity(confidence, conflict_type)

        return KnowledgeConflict(
            knowledge_a=id_a,
            knowledge_b=id_b,
            conflict_type=conflict_type,
            severity=severity,
            confidence=confidence,
            reason=self._reason(conflict_type),
            signals=signals,
        )

    def detect_conflicts(
        self,
        knowledge_objects: list[dict[str, Any]],
    ) -> list[KnowledgeConflict]:
        if not knowledge_objects:
            raise ValueError("Knowledge objects are required")

        conflicts: list[KnowledgeConflict] = []

        for index, knowledge_a in enumerate(knowledge_objects):
            for knowledge_b in knowledge_objects[index + 1:]:
                conflict = self.detect_pair(knowledge_a, knowledge_b)
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def enrich(self, knowledge_objects: list[dict[str, Any]]) -> dict[str, Any]:
        conflicts = self.detect_conflicts(knowledge_objects)

        return {
            "knowledge_objects": knowledge_objects,
            "conflicts": [
                {
                    "knowledge_a": item.knowledge_a,
                    "knowledge_b": item.knowledge_b,
                    "conflict_type": item.conflict_type,
                    "severity": item.severity,
                    "confidence": item.confidence,
                    "reason": item.reason,
                    "signals": item.signals,
                }
                for item in conflicts
            ],
        }

    def _detect_pair_conflict(
        self,
        text_a: str,
        text_b: str,
    ) -> tuple[str, list[str]] | None:
        for left, right, conflict_type in self.CONFLICT_PAIRS:
            if left in text_a and right in text_b:
                return conflict_type, [left, right]
            if right in text_a and left in text_b:
                return conflict_type, [right, left]
        return None

    def _detect_negation_conflict(
        self,
        text_a: str,
        text_b: str,
    ) -> tuple[str, list[str]] | None:
        words_a = set(text_a.split())
        words_b = set(text_b.split())

        shared_words = words_a.intersection(words_b)
        has_negation_a = any(word in text_a for word in self.NEGATION_WORDS)
        has_negation_b = any(word in text_b for word in self.NEGATION_WORDS)

        if shared_words and has_negation_a != has_negation_b:
            return "NEGATION_CONFLICT", list(shared_words)[:3]

        return None

    def _confidence(self, signals: list[str]) -> float:
        if len(signals) >= 3:
            return 0.9
        if len(signals) == 2:
            return 0.8
        return 0.6

    def _severity(self, confidence: float, conflict_type: str) -> str:
        if conflict_type in ["STRATEGY_CONFLICT", "ARCHITECTURE_CONFLICT"] and confidence >= 0.8:
            return "CRITICAL"
        if confidence >= 0.8:
            return "HIGH"
        if confidence >= 0.6:
            return "MEDIUM"
        return "LOW"

    def _reason(self, conflict_type: str) -> str:
        reasons = {
            "CHANNEL_CONFLICT": "Different channel strategies were detected.",
            "OPERATION_CONFLICT": "Different operating methods were detected.",
            "DIRECTION_CONFLICT": "Opposite directional objectives were detected.",
            "STRATEGY_CONFLICT": "Conflicting strategic recommendations were detected.",
            "POSITIONING_CONFLICT": "Different market positioning signals were detected.",
            "EXECUTION_CONFLICT": "Different execution speed assumptions were detected.",
            "ARCHITECTURE_CONFLICT": "Different architecture direction signals were detected.",
            "NEGATION_CONFLICT": "One knowledge object appears to negate another.",
        }
        return reasons.get(conflict_type, "Potential conflict detected.")

    def _collect_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(self._collect_text(v) for v in value.values())
        if isinstance(value, list):
            return " ".join(self._collect_text(v) for v in value)
        return str(value)
