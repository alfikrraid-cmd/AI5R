from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.decision_manufacturing_station import (
    DecisionManufacturingInput,
    DecisionManufacturingStation,
)


def test_station_manufactures_decision_object():
    station = DecisionManufacturingStation()

    result = station.manufacture(
        DecisionManufacturingInput(
            reasoning_object={
                "type": "REASONING_OBJECT",
                "reasoning_id": "RSN-001",
            },
            decision_data={
                "selected_option": "low_risk_action",
                "reason": "limited capital and high uncertainty",
            },
            metadata={"product": "LTSA-AI"},
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-009 Decision Manufacturing Station"
    assert result.decision_object["type"] == "DECISION_OBJECT"
    assert result.decision_id
    assert result.decision_object["decision_id"] == result.decision_id
    assert result.decision_object["decision_data"]["selected_option"] == "low_risk_action"
    assert result.decision_object["metadata"]["product"] == "LTSA-AI"
    assert result.events[0]["event_type"] == "DECISION_MANUFACTURED"


def test_station_requires_reasoning_object():
    station = DecisionManufacturingStation()

    try:
        station.manufacture(
            DecisionManufacturingInput(
                reasoning_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Reasoning object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = DecisionManufacturingStation().manufacture(
        DecisionManufacturingInput(
            reasoning_object={
                "type": "REASONING_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.decision_timestamp)

    assert parsed.tzinfo is not None
