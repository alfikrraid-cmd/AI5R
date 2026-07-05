from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.experience_manufacturing_station import (
    ExperienceManufacturingInput,
    ExperienceManufacturingStation,
)


def test_station_manufactures_experience_object():
    station = ExperienceManufacturingStation()

    result = station.manufacture(
        ExperienceManufacturingInput(
            warehouse_object={
                "type": "WAREHOUSE_OBJECT",
                "warehouse_id": "WH-001",
            }
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-003 Experience Manufacturing Station"
    assert result.experience_object["type"] == "EXPERIENCE_OBJECT"
    assert result.experience_id
    assert result.events[0]["event_type"] == "EXPERIENCE_MANUFACTURED"


def test_station_requires_warehouse_object():
    station = ExperienceManufacturingStation()

    try:
        station.manufacture(
            ExperienceManufacturingInput(
                warehouse_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Warehouse object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = ExperienceManufacturingStation().manufacture(
        ExperienceManufacturingInput(
            warehouse_object={
                "type": "WAREHOUSE_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.experience_timestamp)

    assert parsed.tzinfo is not None
