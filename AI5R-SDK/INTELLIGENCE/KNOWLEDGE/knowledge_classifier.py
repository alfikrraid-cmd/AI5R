from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeClassificationResult:
    domain: str
    category: str
    confidence: float
    signals: list[str] = field(default_factory=list)


class KnowledgeClassificationEngine:
    """
    Classifies extracted knowledge into domain and category.

    This engine is intentionally deterministic first.
    AI classification can be added later, but the factory must have
    a reliable baseline classifier.
    """

    DOMAIN_RULES = {
        "business": [
            "customer", "market", "revenue", "sales", "umkm",
            "profit", "pricing", "subscription", "product",
        ],
        "technical": [
            "api", "database", "workflow", "python", "module",
            "test", "engine", "schema", "integration",
        ],
        "education": [
            "student", "school", "curriculum", "teacher",
            "learning", "class", "assessment",
        ],
        "operation": [
            "process", "pipeline", "station", "manufacturing",
            "factory", "orchestrator", "registry",
        ],
    }

    CATEGORY_RULES = {
        "strategy": ["goal", "plan", "target", "positioning", "roadmap"],
        "implementation": ["build", "create", "develop", "code", "deploy"],
        "validation": ["test", "verify", "check", "evidence", "result"],
        "optimization": ["improve", "increase", "reduce", "optimize", "efficiency"],
    }

    def classify(self, knowledge_object: dict[str, Any]) -> KnowledgeClassificationResult:
        if not knowledge_object:
            raise ValueError("Knowledge object is required")

        text = self._collect_text(knowledge_object).lower()

        domain, domain_signals = self._match_best(text, self.DOMAIN_RULES)
        category, category_signals = self._match_best(text, self.CATEGORY_RULES)

        signals = domain_signals + category_signals
        confidence = self._confidence(len(signals))

        return KnowledgeClassificationResult(
            domain=domain,
            category=category,
            confidence=confidence,
            signals=signals,
        )

    def enrich(self, knowledge_object: dict[str, Any]) -> dict[str, Any]:
        classification = self.classify(knowledge_object)

        enriched = dict(knowledge_object)
        enriched["classification"] = {
            "domain": classification.domain,
            "category": classification.category,
            "confidence": classification.confidence,
            "signals": classification.signals,
        }
        return enriched

    def _collect_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(self._collect_text(v) for v in value.values())
        if isinstance(value, list):
            return " ".join(self._collect_text(v) for v in value)
        return str(value)

    def _match_best(
        self,
        text: str,
        rules: dict[str, list[str]],
    ) -> tuple[str, list[str]]:
        best_label = "general"
        best_signals: list[str] = []

        for label, keywords in rules.items():
            signals = [word for word in keywords if word in text]
            if len(signals) > len(best_signals):
                best_label = label
                best_signals = signals

        return best_label, best_signals

    def _confidence(self, signal_count: int) -> float:
        if signal_count <= 0:
            return 0.25
        if signal_count == 1:
            return 0.45
        if signal_count == 2:
            return 0.65
        if signal_count == 3:
            return 0.8
        return 0.9
