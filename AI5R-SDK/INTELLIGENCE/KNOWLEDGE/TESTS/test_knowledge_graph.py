import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.GRAPH.knowledge_graph import KnowledgeGraph
from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject


def test_graph_builds_nodes_and_edges():
    a = KnowledgeObject(
        knowledge_id="KO-001",
        summary="Pricing strategy",
    )
    a.attach_classification({"domain": "business"})
    a.attach_priority({"priority_level": "HIGH"})
    a.add_relationship({
        "target_id": "KO-002",
        "relationship": "SUPPORTS",
        "confidence": 0.9,
    })

    b = KnowledgeObject(
        knowledge_id="KO-002",
        summary="Revenue growth",
    )
    b.attach_classification({"domain": "business"})
    b.attach_priority({"priority_level": "CRITICAL"})

    graph = KnowledgeGraph().build([a, b])

    assert graph.statistics()["nodes"] == 2
    assert graph.statistics()["edges"] == 1
    assert graph.neighbors("KO-001") == ["KO-002"]


def test_graph_indexes():
    obj = KnowledgeObject(
        knowledge_id="KO-003",
        summary="Curriculum planning",
    )

    obj.attach_classification({"domain": "education"})
    obj.attach_priority({"priority_level": "MEDIUM"})

    graph = KnowledgeGraph().build([obj])

    assert graph.domain_index()["education"] == ["KO-003"]
    assert graph.priority_index()["MEDIUM"] == ["KO-003"]


def test_conflict_index():
    obj = KnowledgeObject(
        knowledge_id="KO-004",
        summary="Conflict sample",
    )

    obj.add_conflict({
        "conflict_type": "CHANNEL_CONFLICT",
        "severity": "HIGH",
    })

    graph = KnowledgeGraph().build([obj])

    assert len(graph.conflict_index()["KO-004"]) == 1
