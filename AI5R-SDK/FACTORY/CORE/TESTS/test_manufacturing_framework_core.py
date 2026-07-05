from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.CORE import (
    BaseManufacturingStation,
    ManufacturingClock,
    ManufacturingID,
    ManufacturingValidationError,
)


class TestStation(BaseManufacturingStation):
    station_code = "MF-TEST"
    station_name = "Test Manufacturing Station"
    object_type = "TEST_OBJECT"
    event_type = "TEST_MANUFACTURED"
    required_input = "source_object"


def test_clock_returns_timezone_aware_timestamp():
    parsed = datetime.fromisoformat(ManufacturingClock.now())

    assert parsed.tzinfo is not None


def test_id_generator_returns_string():
    generated_id = ManufacturingID.generate()

    assert isinstance(generated_id, str)
    assert generated_id


def test_base_station_manufactures_object():
    result = TestStation().manufacture(
        payload={
            "source_object": {
                "type": "SOURCE_OBJECT",
            }
        },
        metadata={
            "product": "LTSA-BRAIN",
        },
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MF-TEST Test Manufacturing Station"
    assert result.manufactured_object["type"] == "TEST_OBJECT"
    assert result.manufactured_object["payload"]["source_object"]["type"] == "SOURCE_OBJECT"
    assert result.manufactured_object["metadata"]["product"] == "LTSA-BRAIN"
    assert result.object_id
    assert result.events[0]["event_type"] == "TEST_MANUFACTURED"


def test_base_station_validates_required_input():
    try:
        TestStation().manufacture(payload={})
    except ManufacturingValidationError as exc:
        assert str(exc) == "Source Object is required"
    else:
        raise AssertionError("Expected ManufacturingValidationError")
