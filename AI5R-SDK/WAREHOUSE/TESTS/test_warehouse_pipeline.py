import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WAREHOUSE.warehouse_pipeline import WarehousePipeline


def test_warehouse_pipeline():
    pipeline = WarehousePipeline()

    obj = pipeline.process(
        source_type="youtube",
        source_id="yt001",
        object_type="raw_transcript",
        payload={
            "title": "Mechanical Seal Basics",
            "content": "Mechanical seal prevents pump leakage."
        },
        organization_id="org001",
        owner_worker_id="worker001",
        tags=["pump", "mechanical-seal", "warehouse"],
        metadata={"created_by": "WF-006-test"},
        policy_ids=["POL-001"]
    )

    assert obj.is_valid()
    assert len(pipeline.list_all()) == 1
    assert pipeline.list_all()[0].source_type == "youtube"

    print(obj.to_dict())
    print("WF-006 Warehouse Pipeline OK")


if __name__ == "__main__":
    test_warehouse_pipeline()
