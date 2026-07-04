from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.manufacturing_pipeline import ManufacturingPipeline


class FirstStation:
    def run(self, payload):
        payload["first"] = True
        payload["status"] = "FIRST_DONE"
        return payload


class SecondStation:
    def run(self, payload):
        payload["second"] = True
        payload["status"] = "SECOND_DONE"
        return payload


def test_manufacturing_pipeline_runs_stations_in_sequence():
    pipeline = ManufacturingPipeline()

    result = (
        pipeline
        .add_station(FirstStation())
        .add_station(SecondStation())
        .run({"product": "AI5R"})
    )

    assert result["status"] == "PIPELINE_COMPLETED"
    assert result["result"]["first"] is True
    assert result["result"]["second"] is True
    assert result["result"]["status"] == "SECOND_DONE"
    assert len(result["history"]) == 2
    assert result["history"][0]["station"] == "FirstStation"
    assert result["history"][1]["station"] == "SecondStation"
