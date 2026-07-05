from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.context_manufacturing_station import (
    ContextManufacturingInput,
    ContextManufacturingStation,
)


def test_station_manufactures_context_object():
    station = ContextManufacturingStation()

    result = station.manufacture(
        ContextManufacturingInput(
            capability_object={
                "type": "CAPABILITY_OBJECT",
                "capability_id": "CAP-001",
            },
            context_data={
                "environment": "business",
                "market": "umkm",
                "constraint": "limited capital",
            },
            metadata={"product": "LTSA-AI"},
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-007 Context Manufacturing Station"
    assert result.context_object["type"] == "CONTEXT_OBJECT"
    assert result.context_id
    assert result.context_object["context_id"] == result.context_id
    assert result.context_object["context_data"]["market"] == "umkm"
    assert result.context_object["metadata"]["product"] == "LTSA-AI"
    assert result.events[0]["event_type"] == "CONTEXT_MANUFACTURED"


def test_station_requires_capability_object():
    station = ContextManufacturingStation()

    try:
        station.manufacture(
            ContextManufacturingInput(
                capability_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Capability object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = ContextManufacturingStation().manufacture(
        ContextManufacturingInput(
            capability_object={
                "type": "CAPABILITY_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.context_timestamp)

    assert parsed.tzinfo is not None
