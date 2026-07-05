import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.knowledge_classifier import KnowledgeClassificationEngine


def test_classifier_detects_business_strategy_knowledge():
    engine = KnowledgeClassificationEngine()

    knowledge = {
        "knowledge_id": "KO-001",
        "summary": "UMKM needs a revenue target and pricing strategy",
        "facts": [
            "customer demand matters",
            "market positioning is important",
        ],
    }

    result = engine.classify(knowledge)

    assert result.domain == "business"
    assert result.category == "strategy"
    assert result.confidence >= 0.8
    assert "umkm" in result.signals
    assert "target" in result.signals


def test_classifier_enriches_knowledge_object():
    engine = KnowledgeClassificationEngine()

    knowledge = {
        "knowledge_id": "KO-002",
        "summary": "Build python module with unit test for API workflow",
    }

    enriched = engine.enrich(knowledge)

    assert enriched["knowledge_id"] == "KO-002"
    assert enriched["classification"]["domain"] == "technical"
    assert enriched["classification"]["category"] in [
        "implementation",
        "validation",
    ]
    assert enriched["classification"]["confidence"] >= 0.65


def test_classifier_handles_general_knowledge():
    engine = KnowledgeClassificationEngine()

    knowledge = {
        "knowledge_id": "KO-003",
        "summary": "This is an abstract idea without known signals",
    }

    result = engine.classify(knowledge)

    assert result.domain == "general"
    assert result.category == "general"
    assert result.confidence == 0.25
