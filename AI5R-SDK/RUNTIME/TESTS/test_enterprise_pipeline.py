import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from REALITY.reality_intake_station import RealityIntakeStation
from REALITY.reality_processing_station import RealityProcessingStation
from WAREHOUSE.warehouse_adapter_station import WarehouseAdapterStation

from RUNTIME.enterprise_pipeline import EnterprisePipeline


def test_pipeline():

    pipeline = EnterprisePipeline()

    pipeline.add_station(
        RealityIntakeStation()
    )

    pipeline.add_station(
        RealityProcessingStation()
    )

    pipeline.add_station(
        WarehouseAdapterStation()
    )

    result = pipeline.execute({

        "source_type": "pump_report",

        "source_name": "sample",

        "raw_content": """
Pump P-101

Seal leakage observed

Vibration 11.2 mm/s

Bearing temperature 92 C
"""
    })

    assert result["object_type"] == "warehouse"

    print("LTSA-007 Enterprise Pipeline OK")


if __name__ == "__main__":
    test_pipeline()
