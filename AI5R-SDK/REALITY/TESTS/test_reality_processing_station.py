import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from REALITY.reality_intake_station import RealityIntakeStation
from REALITY.reality_processing_station import RealityProcessingStation


def test_processing():

    intake = RealityIntakeStation()

    reality = intake.ingest(
        source_type="pump_report",
        source_name="sample.txt",
        raw_content="""
Pump P-101

Seal leakage observed.

Vibration 11.2 mm/s

Bearing temperature 92 C
"""
    )

    processor = RealityProcessingStation()

    result = processor.process(reality)

    assert result["asset"] == "P-101"
    assert result["measurements"]["vibration"] == 11.2
    assert result["measurements"]["temperature"] == 92
    assert "seal_leakage" in result["findings"]

    print("LTSA-006 Reality Processing Station OK")


if __name__ == "__main__":
    test_processing()
