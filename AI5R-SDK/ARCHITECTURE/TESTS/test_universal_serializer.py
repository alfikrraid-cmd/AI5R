import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.universal_object import UniversalObject
from ARCHITECTURE.universal_relationship import UniversalRelationship
from ARCHITECTURE.universal_serializer import UniversalSerializer


def test_universal_object_serialization():

    obj = UniversalObject(
        id="obj001",
        code="OBJ-001",
        name="Serialized Object",
        type="worker",
    )

    obj.set_property("role", "architect")

    payload = UniversalSerializer.to_json(obj)

    restored = UniversalSerializer.from_json(
        UniversalObject,
        payload,
    )

    assert restored.id == obj.id
    assert restored.code == obj.code
    assert restored.properties["role"] == "architect"

    print(restored.to_dict())


def test_universal_relationship_serialization():

    rel = UniversalRelationship(
        id="rel001",
        code="REL-001",
        type="assigned_to",
        source_object_id="worker001",
        target_object_id="mission001",
    )

    rel.set_property("assignment_type", "primary")

    payload = UniversalSerializer.to_json(rel)

    restored = UniversalSerializer.from_json(
        UniversalRelationship,
        payload,
    )

    assert restored.id == rel.id
    assert restored.type == "assigned_to"
    assert restored.properties["assignment_type"] == "primary"

    print(restored.to_dict())


if __name__ == "__main__":
    test_universal_object_serialization()
    test_universal_relationship_serialization()
    print("AX-007 Universal Serializer OK")
