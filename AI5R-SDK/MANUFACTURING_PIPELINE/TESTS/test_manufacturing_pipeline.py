import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MANUFACTURING_PIPELINE import ManufacturingPipeline
from MANUFACTURING_STATION import BaseManufacturingStation
from STATION_REGISTRY import StationRegistry
from WORKFLOW_ENGINE import ManufacturingWorkflow


class SpecificationStation(BaseManufacturingStation):
    station_code = "Specification"
    station_name = "Specification Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["specified"] = True
        return context


class FactoryStation(BaseManufacturingStation):
    station_code = "Factory"
    station_name = "Factory Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["built"] = True
        return context


class RuntimeStation(BaseManufacturingStation):
    station_code = "Runtime"
    station_name = "Runtime Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["running"] = True
        return context


def test_manufacturing_pipeline_runs_workflow():
    registry = StationRegistry()

    registry.register(SpecificationStation())
    registry.register(FactoryStation())
    registry.register(RuntimeStation())

    workflow = ManufacturingWorkflow(
        workflow_name="PRODUCT_PIPELINE",
        stations=[
            "Specification",
            "Factory",
            "Runtime",
        ],
    )

    pipeline = ManufacturingPipeline(registry)

    result = pipeline.run(
        product_name="Digital Employee",
        workflow=workflow,
    )

    assert result["status"] == "PIPELINE_COMPLETED"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert result["payload"]["specified"] is True
    assert result["payload"]["built"] is True
    assert result["payload"]["running"] is True
    assert len(result["history"]) == 3


def test_manufacturing_pipeline_accepts_initial_payload():
    registry = StationRegistry()
    registry.register(SpecificationStation())

    workflow = ManufacturingWorkflow(
        workflow_name="SPEC_ONLY",
        stations=["Specification"],
    )

    pipeline = ManufacturingPipeline(registry)

    result = pipeline.run(
        product_name="Digital Employee",
        workflow=workflow,
        payload={"source": "test"},
    )

    assert result["payload"]["source"] == "test"
    assert result["payload"]["specified"] is True


def test_manufacturing_pipeline_requires_product_name():
    registry = StationRegistry()
    pipeline = ManufacturingPipeline(registry)

    workflow = ManufacturingWorkflow(
        workflow_name="EMPTY",
        stations=["Specification"],
    )

    try:
        pipeline.run("", workflow)
    except ValueError as error:
        assert str(error) == "product_name is required"
    else:
        raise AssertionError("Expected ValueError")
