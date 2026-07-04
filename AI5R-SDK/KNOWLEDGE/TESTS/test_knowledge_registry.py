import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_object import KnowledgeObject
from KNOWLEDGE.knowledge_registry import KnowledgeRegistry


def test_knowledge_registry():
    registry = KnowledgeRegistry()

    knowledge = KnowledgeObject(
        knowledge_id="knowledge-001",
        knowledge_code="KF-001",
        domain="maintenance",
        tags=["pump", "inspection"],
        metadata={"source": "unit-test"},
    )

    registered = registry.register(knowledge)

    assert registered == knowledge
    assert registry.exists("knowledge-001") is True
    assert registry.get("knowledge-001") == knowledge
    assert len(registry.list_all()) == 1

    print("KF-001 Knowledge Registry OK")


if __name__ == "__main__":
    test_knowledge_registry()
