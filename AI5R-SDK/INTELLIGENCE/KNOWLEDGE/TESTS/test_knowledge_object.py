import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject


def test_knowledge_object_requires_id_and_summary():
    knowledge = KnowledgeObject(
        knowledge_id="KO-001",
        summary="Customer demand affects sales growth",
    )

    assert knowledge.validate() is True
    assert knowledge.knowledge_id == "KO-001"


def test_knowledge_object_serializes_to_dict():
    knowledge = KnowledgeObject(
        knowledge_id="KO-002",
        summary="Pricing strategy improves revenue",
        facts=["Revenue depends on pricing"],
        metadata={"source": "test"},
    )

    data = knowledge.to_dict()

    assert data["knowledge_id"] == "KO-002"
    assert data["summary"] == "Pricing strategy improves revenue"
    assert data["facts"] == ["Revenue depends on pricing"]
    assert data["metadata"]["source"] == "test"


def test_knowledge_object_from_dict():
    data = {
        "knowledge_id": "KO-003",
        "summary": "Online sales support UMKM growth",
        "classification": {
            "domain": "business",
            "category": "strategy",
            "confidence": 0.9,
        },
    }

    knowledge = KnowledgeObject.from_dict(data)

    assert knowledge.knowledge_id == "KO-003"
    assert knowledge.classification["domain"] == "business"


def test_knowledge_object_can_attach_classification_and_priority():
    knowledge = KnowledgeObject(
        knowledge_id="KO-004",
        summary="Technical workflow needs validation",
    )

    knowledge.attach_classification({
        "domain": "technical",
        "category": "validation",
        "confidence": 0.8,
    })

    knowledge.attach_priority({
        "priority_score": 0.85,
        "priority_level": "CRITICAL",
    })

    assert knowledge.classification["domain"] == "technical"
    assert knowledge.priority["priority_level"] == "CRITICAL"


def test_knowledge_object_can_add_relationship_and_conflict():
    knowledge = KnowledgeObject(
        knowledge_id="KO-005",
        summary="Online strategy conflicts with offline-first expansion",
    )

    knowledge.add_relationship({
        "target_id": "KO-006",
        "relationship": "RELATED_TO",
        "confidence": 0.7,
    })

    knowledge.add_conflict({
        "knowledge_b": "KO-007",
        "conflict_type": "CHANNEL_CONFLICT",
        "severity": "HIGH",
    })

    assert len(knowledge.relationships) == 1
    assert len(knowledge.conflicts) == 1
    assert knowledge.conflicts[0]["severity"] == "HIGH"

from FOUNDATION.canonical_object import CanonicalObject
from FOUNDATION.canonical_identity import CanonicalIdentityGenerator


def test_knowledge_object_inherits_canonical_object():
    knowledge = KnowledgeObject(
        knowledge_id="KO-006",
        summary="Knowledge object now inherits canonical object",
    )

    assert isinstance(knowledge, CanonicalObject)
    assert knowledge.object_id == "KO-006"
    assert knowledge.object_type == "KNOWLEDGE_OBJECT"
    assert knowledge.knowledge_id == "KO-006"


def test_knowledge_object_can_auto_generate_identity():
    CanonicalIdentityGenerator.reset()

    knowledge = KnowledgeObject(
        summary="Auto generated knowledge identity",
    )

    assert knowledge.knowledge_id.startswith("AI5R-KNOWLEDGE_OBJECT-")
    assert knowledge.object_id == knowledge.knowledge_id
