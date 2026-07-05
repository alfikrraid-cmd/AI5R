from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.memory_manufacturing_station import (
    MemoryManufacturingInput,
    MemoryManufacturingStation,
)


def test_station_manufactures_memory_object():
    station = MemoryManufacturingStation()

    result = station.manufacture(
        MemoryManufacturingInput(
            experience_object={
                "type": "EXPERIENCE_OBJECT",
                "experience_id": "EXP-001",
            },
            metadata={"product": "LTSA-BRAIN"},
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-004 Memory Manufacturing Station"
    assert result.memory_object["type"] == "MEMORY_OBJECT"
    assert result.memory_id
    assert result.memory_object["memory_id"] == result.memory_id
    assert result.memory_object["metadata"]["product"] == "LTSA-BRAIN"
    assert result.events[0]["event_type"] == "MEMORY_MANUFACTURED"


def test_station_requires_experience_object():
    station = MemoryManufacturingStation()

    try:
        station.manufacture(
            MemoryManufacturingInput(
                experience_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Experience object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = MemoryManufacturingStation().manufacture(
        MemoryManufacturingInput(
            experience_object={
                "type": "EXPERIENCE_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.memory_timestamp)

    assert parsed.tzinfo is not None
