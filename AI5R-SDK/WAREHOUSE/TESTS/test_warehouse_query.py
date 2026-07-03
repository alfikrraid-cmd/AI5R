import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WAREHOUSE.warehouse_registry import WarehouseRegistry
from WAREHOUSE.warehouse_ingestion import WarehouseIngestionEngine
from WAREHOUSE.warehouse_query import WarehouseQueryEngine


def test_warehouse_query():
    registry = WarehouseRegistry()
    ingestion = WarehouseIngestionEngine(registry)
    query = WarehouseQueryEngine(registry)

    ingestion.ingest(
        source_type="youtube",
        source_id="yt001",
        object_type="raw_transcript",
        payload={
            "title": "Pump Basics",
            "domain": "pump"
        },
        tags=["pump", "youtube"],
        metadata={"created_by": "WF-004-test"},
        policy_ids=["POL-001"]
    )

    ingestion.ingest(
        source_type="manual",
        source_id="doc001",
        object_type="raw_document",
        payload={
            "title": "Motor Basics",
            "domain": "motor"
        },
        tags=["motor", "manual"],
        metadata={"created_by": "WF-004-test"},
        policy_ids=["POL-002"]
    )

    assert len(query.all()) == 2
    assert len(query.by_tag("pump")) == 1
    assert len(query.by_policy("POL-001")) == 1
    assert len(query.by_metadata("created_by", "WF-004-test")) == 2
    assert len(query.by_payload_field("domain", "motor")) == 1

    print([obj.to_dict() for obj in query.all()])
    print("WF-004 Warehouse Query Engine OK")


if __name__ == "__main__":
    test_warehouse_query()
