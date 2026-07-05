from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.knowledge_manufacturing_station import (
    KnowledgeManufacturingInput,
    KnowledgeManufacturingStation,
)


def test_station_manufactures_knowledge_object():
    station = KnowledgeManufacturingStation()

    result = station.manufacture(
        KnowledgeManufacturingInput(
            memory_object={
                "type": "MEMORY_OBJECT",
                "memory_id": "MEM-001",
            },
            metadata={"product": "LTSA-BRAIN"},
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-005 Knowledge Manufacturing Station"
    assert result.knowledge_object["type"] == "KNOWLEDGE_OBJECT"
    assert result.knowledge_id
    assert result.knowledge_object["knowledge_id"] == result.knowledge_id
    assert result.knowledge_object["metadata"]["product"] == "LTSA-BRAIN"
    assert result.events[0]["event_type"] == "KNOWLEDGE_MANUFACTURED"


def test_station_requires_memory_object():
    station = KnowledgeManufacturingStation()

    try:
        station.manufacture(
            KnowledgeManufacturingInput(
                memory_object={}
            )
        )
    except ValueError as exc:
        assert str(exc) == "Memory object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = KnowledgeManufacturingStation().manufacture(
        KnowledgeManufacturingInput(
            memory_object={
                "type": "MEMORY_OBJECT"
            }
        )
    )

    parsed = datetime.fromisoformat(result.knowledge_timestamp)

    assert parsed.tzinfo is not None
