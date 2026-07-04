import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from REALITY.reality_intake_station import RealityIntakeStation


def test_reality_intake_station_ingests_pump_report():
    station = RealityIntakeStation()

    reality = station.ingest(
        source_type="pump_report",
        source_name="pump_report_sample.txt",
        raw_content="Pump P-101 vibration is high. Seal leakage observed.",
        metadata={
            "asset": "P-101",
            "plant": "LTSA-DEMO",
        },
    )

    assert reality["object_type"] == "reality"
    assert reality["station"] == "reality_intake"
    assert reality["source_type"] == "pump_report"
    assert reality["status"] == "ingested"
    assert "Pump P-101" in reality["raw_content"]
    assert reality["metadata"]["asset"] == "P-101"


if __name__ == "__main__":
    test_reality_intake_station_ingests_pump_report()
    print("LTSA-004 Reality Intake Station OK")
