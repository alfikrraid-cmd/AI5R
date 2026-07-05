import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.knowledge_conflict_detector import (
    KnowledgeConflictDetectionEngine,
)


def test_detects_channel_conflict():
    engine = KnowledgeConflictDetectionEngine()

    knowledge_a = {
        "knowledge_id": "KN-001",
        "summary": "UMKM should focus on online sales first",
    }
    knowledge_b = {
        "knowledge_id": "KN-002",
        "summary": "UMKM should focus on offline store expansion first",
    }

    conflict = engine.detect_pair(knowledge_a, knowledge_b)

    assert conflict is not None
    assert conflict.conflict_type == "CHANNEL_CONFLICT"
    assert conflict.severity == "HIGH"
    assert conflict.confidence >= 0.8


def test_detects_strategy_conflict():
    engine = KnowledgeConflictDetectionEngine()

    knowledge_a = {
        "knowledge_id": "KN-003",
        "summary": "The company should expand product lines this quarter",
    }
    knowledge_b = {
        "knowledge_id": "KN-004",
        "summary": "The company should limit product lines this quarter",
    }

    conflict = engine.detect_pair(knowledge_a, knowledge_b)

    assert conflict is not None
    assert conflict.conflict_type == "STRATEGY_CONFLICT"
    assert conflict.severity == "CRITICAL"


def test_detect_conflicts_returns_only_conflicts():
    engine = KnowledgeConflictDetectionEngine()

    knowledge_objects = [
        {"knowledge_id": "KN-001", "summary": "Use premium positioning"},
        {"knowledge_id": "KN-002", "summary": "Use cheap positioning"},
        {"knowledge_id": "KN-003", "summary": "Improve customer service"},
    ]

    conflicts = engine.detect_conflicts(knowledge_objects)

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "POSITIONING_CONFLICT"


def test_enrich_adds_conflict_list():
    engine = KnowledgeConflictDetectionEngine()

    knowledge_objects = [
        {"knowledge_id": "KN-001", "summary": "Use manual process"},
        {"knowledge_id": "KN-002", "summary": "Use automatic process"},
    ]

    enriched = engine.enrich(knowledge_objects)

    assert "conflicts" in enriched
    assert len(enriched["conflicts"]) == 1
    assert enriched["conflicts"][0]["severity"] == "HIGH"
