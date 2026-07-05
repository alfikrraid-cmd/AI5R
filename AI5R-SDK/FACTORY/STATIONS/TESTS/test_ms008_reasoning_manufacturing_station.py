from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.reasoning_manufacturing_station import (
    ReasoningManufacturingInput,
    ReasoningManufacturingStation,
)


def test_station_manufactures_reasoning_object():
    station = ReasoningManufacturingStation()

    result = station.manufacture(
        ReasoningManufacturingInput(
            context_object={
                "type": "CONTEXT_OBJECT",
                "context_id": "CTX-001",
            },
            reasoning_data={
                "hypothesis": "limited capital requires low-risk action",
                "basis": "context constraint",
            },
            metadata={"product": "LTSA-AI"},
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-008 Reasoning Manufacturing Station"
    assert result.reasoning_object["type"] == "REASONING_OBJECT"
    assert result.reasoning_id
    assert result.reasoning_object["reasoning_id"] == result.reasoning_id
    assert result.reasoning_object["reasoning_data"]["basis"] == "context constraint"
    assert result.reasoning_object["metadata"]["product"] == "LTSA-AI"
    assert result.events[0]["event_type"] == "REASONING_MANUFACTURED"


def test_station_requires_context_object():
    station = ReasoningManufacturingStation()

    try:
        station.manufacture(
            ReasoningManufacturingInput(
                context_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Context object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = ReasoningManufacturingStation().manufacture(
        ReasoningManufacturingInput(
            context_object={
                "type": "CONTEXT_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.reasoning_timestamp)

    assert parsed.tzinfo is not None
