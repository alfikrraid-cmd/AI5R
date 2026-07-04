import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_object import KnowledgeObject


def test_knowledge_object_supports_legacy_registry_contract():
    obj = KnowledgeObject(
        organization_id="ORG-001",
        department_id="DEP-001",
        owner_worker_id="WRK-001",
        knowledge_code="KNW-001",
        title="Pump Knowledge",
        content="Pump maintenance knowledge",
        source_type="MANUAL",
        metadata={"domain": "maintenance"},
    )

    assert obj.organization_id == "ORG-001"
    assert obj.department_id == "DEP-001"
    assert obj.owner_worker_id == "WRK-001"
    assert obj.knowledge_code == "KNW-001"
    assert obj.knowledge_id == "KNW-001"


def test_knowledge_object_supports_memory_contract():
    obj = KnowledgeObject(
        knowledge_id="knowledge-001",
        source_memory_ids=["memory-001", "memory-002"],
        domain="maintenance",
        confidence=0.95,
        digital_thread_id="thread-001",
    )

    assert obj.knowledge_id == "knowledge-001"
    assert obj.source_memory_ids == ["memory-001", "memory-002"]
    assert obj.domain == "maintenance"
    assert obj.confidence == 0.95


def test_knowledge_object_to_dict_contains_all_contract_fields():
    obj = KnowledgeObject(
        organization_id="ORG-002",
        department_id="DEP-002",
        owner_worker_id="WRK-002",
        knowledge_code="KNW-002",
        source_memory_ids=["memory-003"],
    )

    data = obj.to_dict()

    assert data["organization_id"] == "ORG-002"
    assert data["department_id"] == "DEP-002"
    assert data["owner_worker_id"] == "WRK-002"
    assert data["knowledge_code"] == "KNW-002"
    assert data["source_memory_ids"] == ["memory-003"]
