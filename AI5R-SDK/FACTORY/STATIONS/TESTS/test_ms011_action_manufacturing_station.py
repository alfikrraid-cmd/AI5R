from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.action_manufacturing_station import (
    ActionManufacturingInput,
    ActionManufacturingStation,
)


def test_station_manufactures_action_object():
    station = ActionManufacturingStation()

    result = station.manufacture(
        ActionManufacturingInput(
            recommendation_object={
                "type": "RECOMMENDATION_OBJECT",
                "recommendation_id": "REC-001",
            },
            action_data={
                "action": "run_validation_experiment",
                "priority": "high",
            },
            metadata={"product": "LTSA-AI"},
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-011 Action Manufacturing Station"
    assert result.action_object["type"] == "ACTION_OBJECT"
    assert result.action_id
    assert result.action_object["action_id"] == result.action_id
    assert result.action_object["action_data"]["action"] == "run_validation_experiment"
    assert result.action_object["metadata"]["product"] == "LTSA-AI"
    assert result.events[0]["event_type"] == "ACTION_MANUFACTURED"


def test_station_requires_recommendation_object():
    station = ActionManufacturingStation()

    try:
        station.manufacture(
            ActionManufacturingInput(
                recommendation_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Recommendation object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = ActionManufacturingStation().manufacture(
        ActionManufacturingInput(
            recommendation_object={
                "type": "RECOMMENDATION_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.action_timestamp)

    assert parsed.tzinfo is not None
