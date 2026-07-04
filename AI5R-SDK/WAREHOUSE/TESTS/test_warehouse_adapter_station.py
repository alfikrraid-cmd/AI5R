import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from REALITY.reality_intake_station import RealityIntakeStation
from WAREHOUSE.warehouse_adapter_station import WarehouseAdapterStation


def test_warehouse_adapter_station_adapts_reality_object():
    intake = RealityIntakeStation()
    adapter = WarehouseAdapterStation()

    reality = intake.ingest(
        source_type="pump_report",
        source_name="report.pdf",
        raw_content="Bearing damage detected.",
    )

    warehouse = adapter.adapt(reality)

    assert warehouse["object_type"] == "warehouse"
    assert warehouse["entity_type"] == "pump_report"
    assert warehouse["payload"]["object_type"] == "reality"
    assert warehouse["payload"]["raw_content"] == "Bearing damage detected."
    assert warehouse["status"] == "adapted"


if __name__ == "__main__":
    test_warehouse_adapter_station_adapts_reality_object()
    print("LTSA-005 Warehouse Adapter Station OK")
