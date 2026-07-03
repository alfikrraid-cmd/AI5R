import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.universal_relationship import UniversalRelationship


def test_universal_relationship():

    rel = UniversalRelationship(
        id="rel001",
        code="REL-001",
        type="assigned_to",
        source_object_id="worker001",
        target_object_id="mission001",
    )

    rel.set_property("assignment_type", "primary")
    rel.set_metadata("created_by", "AX-005-test")
    rel.add_policy("POL-001")

    assert rel.type == "assigned_to"
    assert rel.source_object_id == "worker001"
    assert rel.target_object_id == "mission001"
    assert rel.properties["assignment_type"] == "primary"
    assert rel.metadata["created_by"] == "AX-005-test"
    assert "POL-001" in rel.policy_ids
    assert rel.is_directed() is True

    print(rel.to_dict())
    print("AX-005 Universal Relationship OK")


if __name__ == "__main__":
    test_universal_relationship()
