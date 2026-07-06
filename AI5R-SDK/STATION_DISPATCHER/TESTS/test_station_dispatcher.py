import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MANUFACTURING_STATION import (
    BaseManufacturingStation,
    ManufacturingContext,
)
from STATION_REGISTRY import StationRegistry
from STATION_DISPATCHER import StationDispatcher
from WORKFLOW_ENGINE import ManufacturingWorkflow


class SpecStation(BaseManufacturingStation):
    station_code = "Specification"
    station_name = "Specification Station"


class FactoryStation(BaseManufacturingStation):
    station_code = "Factory"
    station_name = "Factory Station"


class RuntimeStation(BaseManufacturingStation):
    station_code = "Runtime"
    station_name = "Runtime Station"


def test_dispatcher_executes_workflow():
    registry = StationRegistry()

    registry.register(SpecStation())
    registry.register(FactoryStation())
    registry.register(RuntimeStation())

    workflow = ManufacturingWorkflow(
        workflow_name="TEST",
        stations=[
            "Specification",
            "Factory",
            "Runtime",
        ],
    )

    dispatcher = StationDispatcher(registry)

    context = ManufacturingContext(
        product="DIGITAL_EMPLOYEE"
    )

    result = dispatcher.dispatch(workflow, context)

    assert len(result.history) == 3
    assert result.history[0]["station_code"] == "Specification"
    assert result.history[1]["station_code"] == "Factory"
    assert result.history[2]["station_code"] == "Runtime"


def test_dispatcher_requires_registered_station():
    registry = StationRegistry()

    workflow = ManufacturingWorkflow(
        workflow_name="BROKEN",
        stations=["Factory"],
    )

    dispatcher = StationDispatcher(registry)

    context = ManufacturingContext(product="TEST")

    try:
        dispatcher.dispatch(workflow, context)
    except ValueError as error:
        assert "not registered" in str(error)
    else:
        raise AssertionError("Expected ValueError")
