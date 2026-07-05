import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.knowledge_prioritizer import (
    KnowledgePrioritizationEngine,
)


def test_priority_high():
    engine = KnowledgePrioritizationEngine()

    knowledge = {
        "impact": 0.9,
        "urgency": 0.9,
        "actionability": 0.8,
        "classification": {
            "confidence": 0.9,
        },
    }

    result = engine.prioritize(knowledge)

    assert result.priority_level == "CRITICAL"
    assert result.priority_score >= 0.85


def test_priority_medium():
    engine = KnowledgePrioritizationEngine()

    knowledge = {
        "impact": 0.6,
        "urgency": 0.5,
        "actionability": 0.6,
        "classification": {
            "confidence": 0.5,
        },
    }

    result = engine.prioritize(knowledge)

    assert result.priority_level == "MEDIUM"


def test_enrich():
    engine = KnowledgePrioritizationEngine()

    knowledge = {
        "impact": 1.0,
        "urgency": 0.8,
        "actionability": 0.9,
        "classification": {
            "confidence": 0.9,
        },
    }

    enriched = engine.enrich(knowledge)

    assert "priority" in enriched
    assert enriched["priority"]["priority_level"] == "CRITICAL"
