import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WAREHOUSE.warehouse_object import WarehouseObject
from WAREHOUSE.warehouse_registry import WarehouseRegistry


def test_warehouse_registry():
    registry = WarehouseRegistry()

    obj = WarehouseObject(
        id="wh001",
        code="WH-001",
        source_type="youtube",
        source_id="yt001",
        object_type="raw_transcript",
        payload={
            "title": "Mechanical Seal Basics",
            "content": "Mechanical seal prevents leakage..."
        },
        tags=["pump", "mechanical-seal"]
    )

    registry.register(obj)

    assert registry.get("wh001") == obj
    assert len(registry.list_all()) == 1
    assert len(registry.find_by_source("youtube", "yt001")) == 1
    assert len(registry.find_by_object_type("raw_transcript")) == 1

    print(registry.get("wh001").to_dict())
    print("WF-002 Warehouse Registry Engine OK")


if __name__ == "__main__":
    test_warehouse_registry()
