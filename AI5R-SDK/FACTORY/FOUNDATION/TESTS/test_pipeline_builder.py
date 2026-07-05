from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.station_registry import StationRegistry
from FACTORY.FOUNDATION.pipeline_builder import PipelineBuilder


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


def test_pipeline_builder_builds_pipeline_from_registry():
    registry = StationRegistry()
    registry.register("first", FirstStation())
    registry.register("second", SecondStation())

    builder = PipelineBuilder(registry)

    pipeline = builder.build(["first", "second"])

    result = pipeline.run({"product": "AI5R"})

    assert result["status"] == "PIPELINE_COMPLETED"
    assert result["result"]["first"] is True
    assert result["result"]["second"] is True
    assert len(result["history"]) == 2


def test_pipeline_builder_rejects_unknown_station():
    registry = StationRegistry()
    builder = PipelineBuilder(registry)

    try:
        builder.build(["missing"])
        assert False
    except ValueError as error:
        assert "not registered" in str(error)
