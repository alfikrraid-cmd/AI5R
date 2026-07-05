from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.manufacturing_event import ManufacturingEvent
from FACTORY.FOUNDATION.manufacturing_event_bus import ManufacturingEventBus


def test_event_bus():
    bus = ManufacturingEventBus()

    event = ManufacturingEvent(
        event_type="BUILD_STARTED",
        station="Reality",
        build_id="BUILD-001",
        product="LTSA-BRAIN",
    )

    bus.publish(event)

    assert len(bus.all()) == 1

    assert bus.all()[0].event_type == "BUILD_STARTED"


def test_event_to_dict():

    event = ManufacturingEvent(
        event_type="DONE",
        station="Knowledge",
        build_id="BUILD-2",
        product="OSA",
    )

    data = event.to_dict()

    assert data["station"] == "Knowledge"

    assert data["event_type"] == "DONE"
