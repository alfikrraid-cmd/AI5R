import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_object import KnowledgeObject


def test_knowledge_object():

    obj = KnowledgeObject(

        knowledge_id="knowledge-001",

        source_memory_ids=[
            "memory-001",
            "memory-002",
        ],

        domain="maintenance",

        confidence=0.95,

        digital_thread_id="thread-001",
    )

    assert obj.status == "knowledge"

    assert obj.domain == "maintenance"

    assert len(obj.source_memory_ids) == 2


def test_to_dict():

    obj = KnowledgeObject(

        knowledge_id="knowledge-002",

        source_memory_ids=[],

        domain="general",
    )

    data = obj.to_dict()

    assert data["knowledge_id"] == "knowledge-002"

    assert data["status"] == "knowledge"
