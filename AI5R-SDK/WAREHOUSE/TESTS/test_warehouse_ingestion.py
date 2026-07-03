import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WAREHOUSE.warehouse_registry import WarehouseRegistry
from WAREHOUSE.warehouse_ingestion import WarehouseIngestionEngine


def test_warehouse_ingestion():
    registry = WarehouseRegistry()
    engine = WarehouseIngestionEngine(registry)

    obj = engine.ingest(
        source_type="youtube",
        source_id="yt001",
        object_type="raw_transcript",
        payload={
            "title": "Pump Basics",
            "content": "A centrifugal pump converts rotational energy..."
        },
        organization_id="org001",
        owner_worker_id="worker001",
        tags=["pump", "youtube", "raw"],
        metadata={
            "created_by": "WF-003-test"
        },
        policy_ids=["POL-001"]
    )

    assert obj.is_valid()
    assert obj.source_type == "youtube"
    assert obj.source_id == "yt001"
    assert obj.object_type == "raw_transcript"
    assert registry.get(obj.id) == obj
    assert len(registry.list_all()) == 1

    print(obj.to_dict())
    print("WF-003 Warehouse Ingestion Engine OK")


if __name__ == "__main__":
    test_warehouse_ingestion()
