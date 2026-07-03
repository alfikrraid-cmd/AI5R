import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_object import KnowledgeObject
from KNOWLEDGE.knowledge_registry import KnowledgeRegistry


def test_knowledge_registry():
    registry = KnowledgeRegistry()

    item = KnowledgeObject(
        organization_id="ORG-001",
        department_id="DEPT-ENG-001",
        owner_worker_id="WORKER-001",
        knowledge_code="KNW-LTSA-001",
        title="LTSA Brain Pump Knowledge",
        content="Pump registry contains pump assets, specifications, and operating context.",
        source_type="MANUAL",
        metadata={
            "domain": "power_plant",
            "criticality": "high",
        },
    )

    registry.register(item)

    assert registry.get(item.knowledge_id).title == "LTSA Brain Pump Knowledge"
    assert len(registry.list_by_organization("ORG-001")) == 1
    assert len(registry.list_by_department("DEPT-ENG-001")) == 1
    assert registry.search("ORG-001", "pump")[0].knowledge_code == "KNW-LTSA-001"

    print("KF-001 Knowledge Registry OK")


if __name__ == "__main__":
    test_knowledge_registry()
