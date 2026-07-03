import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WAREHOUSE.warehouse_pipeline import WarehousePipeline
from WAREHOUSE.warehouse_export import WarehouseExportContract


def test_warehouse_export():
    pipeline = WarehousePipeline()
    exporter = WarehouseExportContract()

    obj = pipeline.process(
        source_type="youtube",
        source_id="yt001",
        object_type="raw_transcript",
        payload={
            "title": "Pump Maintenance",
            "content": "Pump maintenance requires inspection."
        },
        organization_id="org001",
        owner_worker_id="worker001",
        tags=["pump", "export"],
        metadata={"created_by": "WF-007-test"},
        policy_ids=["POL-001"]
    )

    exported = exporter.export_object(obj)

    assert exported["warehouse_id"] == obj.id
    assert exported["source"]["type"] == "youtube"
    assert exported["source"]["id"] == "yt001"
    assert exported["object_type"] == "raw_transcript"
    assert exported["payload"]["title"] == "Pump Maintenance"
    assert exported["context"]["organization_id"] == "org001"

    batch = exporter.export_batch(pipeline.list_all())
    assert len(batch) == 1

    print(exported)
    print("WF-007 Warehouse Export Contract OK")


if __name__ == "__main__":
    test_warehouse_export()
