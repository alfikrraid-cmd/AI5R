import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_event import CanonicalEvent
from FOUNDATION.canonical_object import CanonicalObject


def test_canonical_event_validates_required_fields():
    event = CanonicalEvent(
        event_id="EV-001",
        event_type="OBJECT_CREATED",
        source_object_id="OBJ-001",
        source_object_type="TEST_OBJECT",
    )

    assert event.validate() is True


def test_canonical_event_serializes():
    event = CanonicalEvent(
        event_id="EV-002",
        event_type="KNOWLEDGE_CLASSIFIED",
        source_object_id="KO-001",
        source_object_type="KNOWLEDGE_OBJECT",
        payload={"domain": "business"},
        metadata={"source": "unit-test"},
    )

    data = event.serialize()

    assert data["event_id"] == "EV-002"
    assert data["event_type"] == "KNOWLEDGE_CLASSIFIED"
    assert data["payload"]["domain"] == "business"
    assert data["metadata"]["source"] == "unit-test"
    assert data["timestamp"].endswith("Z")


def test_canonical_event_deserializes():
    data = {
        "event_id": "EV-003",
        "event_type": "MEMORY_MANUFACTURED",
        "source_object_id": "MO-001",
        "source_object_type": "MEMORY_OBJECT",
        "payload": {"status": "created"},
    }

    event = CanonicalEvent.deserialize(data)

    assert event.event_id == "EV-003"
    assert event.source_object_id == "MO-001"
    assert event.payload["status"] == "created"


def test_canonical_event_can_be_created_from_object():
    obj = CanonicalObject(
        object_id="OBJ-004",
        object_type="TEST_OBJECT",
    )

    event = CanonicalEvent.from_object(
        event_id="EV-004",
        event_type="OBJECT_UPDATED",
        source_object=obj,
        payload={"field": "summary"},
    )

    assert event.source_object_id == "OBJ-004"
    assert event.source_object_type == "TEST_OBJECT"
    assert event.payload["field"] == "summary"
