import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.knowledge_relationship_engine import (
    KnowledgeRelationshipEngine,
)


def test_relationship_detects_dependency():
    engine = KnowledgeRelationshipEngine()

    source = {
        "knowledge_id": "KN-001",
        "summary": "Sales growth requires customer research",
    }
    target = {
        "knowledge_id": "KN-002",
        "summary": "Customer research is needed before pricing strategy",
    }

    result = engine.analyze_pair(source, target)

    assert result.source_id == "KN-001"
    assert result.target_id == "KN-002"
    assert result.relationship == "DEPENDS_ON"
    assert result.confidence >= 0.55


def test_relationship_detects_implementation():
    engine = KnowledgeRelationshipEngine()

    source = {
        "knowledge_id": "KN-003",
        "summary": "Build python module for workflow execution",
    }
    target = {
        "knowledge_id": "KN-004",
        "summary": "Deploy API integration after unit test",
    }

    result = engine.analyze_pair(source, target)

    assert result.relationship == "IMPLEMENTS"
    assert result.confidence >= 0.75


def test_relationship_graph_creates_edges():
    engine = KnowledgeRelationshipEngine()

    knowledge_objects = [
        {"knowledge_id": "KN-001", "summary": "Revenue increase needs pricing strategy"},
        {"knowledge_id": "KN-002", "summary": "Pricing strategy supports customer growth"},
        {"knowledge_id": "KN-003", "summary": "Customer growth leads to stronger sales"},
    ]

    graph = engine.enrich_graph(knowledge_objects)

    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["edges"]) == 3
    assert graph["edges"][0]["source_id"] == "KN-001"
