import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.universal_object import UniversalObject


def test_universal_object():

    obj = UniversalObject(
        id="obj001",
        code="OBJ-001",
        name="Test Object",
        type="worker",
    )

    obj.add_tag("engineering")
    obj.add_label("chief")
    obj.set_property("role", "architect")

    assert obj.properties["role"] == "architect"
    assert obj.type == "worker"
    assert obj.code == "OBJ-001"

    print(obj.to_dict())
    print("AX-004 Universal Object OK")


if __name__ == "__main__":
    test_universal_object()
