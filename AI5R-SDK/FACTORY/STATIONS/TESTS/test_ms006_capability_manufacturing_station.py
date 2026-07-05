from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.capability_manufacturing_station import (
    CapabilityManufacturingInput,
    CapabilityManufacturingStation,
)


def test_station_manufactures_capability_object():
    station = CapabilityManufacturingStation()

    result = station.manufacture(
        CapabilityManufacturingInput(
            knowledge_object={
                "type": "KNOWLEDGE_OBJECT",
                "knowledge_id": "KN-001",
            }
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-006 Capability Manufacturing Station"
    assert result.capability_object["type"] == "CAPABILITY_OBJECT"
    assert result.capability_id
    assert result.events[0]["event_type"] == "CAPABILITY_MANUFACTURED"


def test_station_requires_knowledge_object():
    station = CapabilityManufacturingStation()

    try:
        station.manufacture(
            CapabilityManufacturingInput(
                knowledge_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Knowledge object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = CapabilityManufacturingStation().manufacture(
        CapabilityManufacturingInput(
            knowledge_object={
                "type": "KNOWLEDGE_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.capability_timestamp)

    assert parsed.tzinfo is not None
