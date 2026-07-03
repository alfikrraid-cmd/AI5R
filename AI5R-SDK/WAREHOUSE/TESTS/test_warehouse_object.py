import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WAREHOUSE.warehouse_object import WarehouseObject


def test_warehouse_object():
    obj = WarehouseObject(
        id="wh001",
        code="WH-001",
        source_type="reality",
        source_id="youtube-transcript-001",
        object_type="raw_knowledge_input",
        payload={
            "title": "Pump Maintenance Explanation",
            "content": "Mechanical seal maintenance steps..."
        },
        organization_id="org001",
        owner_worker_id="worker001",
        tags=["pump", "maintenance", "raw-input"],
        metadata={
            "created_by": "WF-001-test"
        },
        policy_ids=["POL-001"]
    )

    assert obj.is_valid()
    data = obj.to_dict()

    assert data["id"] == "wh001"
    assert data["code"] == "WH-001"
    assert data["source_type"] == "reality"
    assert data["object_type"] == "raw_knowledge_input"
    assert data["payload"]["title"] == "Pump Maintenance Explanation"

    print(data)
    print("WF-001 Warehouse Object OK")


if __name__ == "__main__":
    test_warehouse_object()
