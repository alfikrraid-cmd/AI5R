import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.GRAPH.knowledge_graph import KnowledgeGraph
from INTELLIGENCE.KNOWLEDGE.GRAPH.knowledge_graph_query import (
    KnowledgeGraphQueryEngine,
)
from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject


def build_sample_graph():
    a = KnowledgeObject(
        knowledge_id="KO-Q001",
        summary="UMKM pricing strategy increases revenue",
    )
    a.attach_classification({"domain": "business"})
    a.attach_priority({"priority_level": "HIGH"})
    a.add_relationship({
        "target_id": "KO-Q002",
        "relationship": "SUPPORTS",
        "confidence": 0.9,
    })

    b = KnowledgeObject(
        knowledge_id="KO-Q002",
        summary="Revenue growth depends on customer demand",
    )
    b.attach_classification({"domain": "business"})
    b.attach_priority({"priority_level": "CRITICAL"})

    c = KnowledgeObject(
        knowledge_id="KO-Q003",
        summary="School curriculum needs assessment",
    )
    c.attach_classification({"domain": "education"})
    c.attach_priority({"priority_level": "MEDIUM"})
    c.add_conflict({
        "conflict_type": "STRATEGY_CONFLICT",
        "severity": "HIGH",
    })

    return KnowledgeGraph().build([a, b, c])


def test_query_get_node():
    query = KnowledgeGraphQueryEngine(build_sample_graph())

    obj = query.get("KO-Q001")

    assert obj is not None
    assert obj.summary == "UMKM pricing strategy increases revenue"


def test_query_by_domain():
    query = KnowledgeGraphQueryEngine(build_sample_graph())

    results = query.by_domain("business")

    assert len(results) == 2
    assert results[0].classification["domain"] == "business"


def test_query_by_priority():
    query = KnowledgeGraphQueryEngine(build_sample_graph())

    results = query.by_priority("CRITICAL")

    assert len(results) == 1
    assert results[0].knowledge_id == "KO-Q002"


def test_query_related_to():
    query = KnowledgeGraphQueryEngine(build_sample_graph())

    results = query.related_to("KO-Q001")

    assert len(results) == 1
    assert results[0].knowledge_id == "KO-Q002"


def test_query_conflicts_for():
    query = KnowledgeGraphQueryEngine(build_sample_graph())

    conflicts = query.conflicts_for("KO-Q003")

    assert len(conflicts) == 1
    assert conflicts[0]["severity"] == "HIGH"


def test_query_high_value():
    query = KnowledgeGraphQueryEngine(build_sample_graph())

    results = query.high_value()
    ids = [item.knowledge_id for item in results]

    assert "KO-Q001" in ids
    assert "KO-Q002" in ids
    assert "KO-Q003" not in ids


def test_query_search_summary():
    query = KnowledgeGraphQueryEngine(build_sample_graph())

    results = query.search_summary("pricing")

    assert len(results) == 1
    assert results[0].knowledge_id == "KO-Q001"
