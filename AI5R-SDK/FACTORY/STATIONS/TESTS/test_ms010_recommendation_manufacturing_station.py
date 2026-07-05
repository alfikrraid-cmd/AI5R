from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.recommendation_manufacturing_station import (
    RecommendationManufacturingInput,
    RecommendationManufacturingStation,
)


def test_station_manufactures_recommendation_object():
    station = RecommendationManufacturingStation()

    result = station.manufacture(
        RecommendationManufacturingInput(
            decision_object={
                "type": "DECISION_OBJECT",
                "decision_id": "DEC-001",
            },
            recommendation_data={
                "recommendation": "start with a low-risk validation experiment",
                "priority": "high",
            },
            metadata={"product": "LTSA-AI"},
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-010 Recommendation Manufacturing Station"
    assert result.recommendation_object["type"] == "RECOMMENDATION_OBJECT"
    assert result.recommendation_id
    assert result.recommendation_object["recommendation_id"] == result.recommendation_id
    assert result.recommendation_object["recommendation_data"]["priority"] == "high"
    assert result.recommendation_object["metadata"]["product"] == "LTSA-AI"
    assert result.events[0]["event_type"] == "RECOMMENDATION_MANUFACTURED"


def test_station_requires_decision_object():
    station = RecommendationManufacturingStation()

    try:
        station.manufacture(
            RecommendationManufacturingInput(
                decision_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Decision object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = RecommendationManufacturingStation().manufacture(
        RecommendationManufacturingInput(
            decision_object={
                "type": "DECISION_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.recommendation_timestamp)

    assert parsed.tzinfo is not None
