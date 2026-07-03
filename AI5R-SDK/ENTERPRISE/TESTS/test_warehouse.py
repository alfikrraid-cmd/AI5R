import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ENTERPRISE.enterprise_object import EnterpriseObject
from ENTERPRISE.warehouse import Warehouse


def test_warehouse():
    warehouse = Warehouse("knowledge")

    item = EnterpriseObject(
        code="KNOW-001",
        name="LTSA Pump Knowledge",
        type="knowledge",
        owner="Knowledge Factory",
        tags=["ltsa", "pump", "industrial"],
        metadata={
            "source": "manual",
            "confidence": 0.9,
        },
    )

    warehouse.store(item)

    assert warehouse.load("KNOW-001").name == "LTSA Pump Knowledge"
    assert len(warehouse.list()) == 1

    warehouse.version("KNOW-001", "1.1.0")
    assert warehouse.load("KNOW-001").version == "1.1.0"

    warehouse.publish("KNOW-001")
    assert warehouse.load("KNOW-001").status == "published"

    result = warehouse.search_by_tag("pump")
    assert len(result) == 1
    assert result[0].code == "KNOW-001"

    warehouse.archive("KNOW-001")
    assert warehouse.load("KNOW-001").status == "archived"

    data = warehouse.to_dict()
    assert data["warehouse_type"] == "knowledge"
    assert data["count"] == 1

    print("EL-005 Warehouse Framework OK")


if __name__ == "__main__":
    test_warehouse()
