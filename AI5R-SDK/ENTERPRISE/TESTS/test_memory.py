import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ENTERPRISE.enterprise_object import EnterpriseObject
from ENTERPRISE.memory import Memory


def test_memory():
    memory = Memory("mission_memory")

    entry = EnterpriseObject(
        code="MEM-001",
        name="LTSA Build Mission Lesson",
        type="mission_memory",
        owner="Mission Control",
        tags=["ltsa", "mission", "lesson"],
        metadata={
            "mission_id": "MISSION-001",
            "summary": "Factory foundation must remain frozen before Enterprise Layer expansion.",
            "confidence": 0.95,
        },
    )

    memory.remember(entry)

    assert memory.recall("MEM-001").name == "LTSA Build Mission Lesson"
    assert len(memory.list()) == 1

    result = memory.search_by_tag("lesson")
    assert len(result) == 1
    assert result[0].code == "MEM-001"

    memory.mark_processed("MEM-001")
    assert memory.recall("MEM-001").status == "processed"

    memory.archive("MEM-001")
    assert memory.recall("MEM-001").status == "archived"

    data = memory.to_dict()
    assert data["memory_type"] == "mission_memory"
    assert data["count"] == 1

    print("EL-006 Memory Framework OK")


if __name__ == "__main__":
    test_memory()
