import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_object import CanonicalObject, utc_now_iso
from FOUNDATION.canonical_identity import CanonicalIdentityGenerator


def setup_function():
    CanonicalIdentityGenerator.reset()


def test_utc_now_iso_returns_zulu_time():
    value = utc_now_iso()

    assert value.endswith("Z")
    assert "+00:00" not in value


def test_canonical_object_validates_required_fields():
    obj = CanonicalObject(
        object_id="OBJ-001",
        object_type="TEST_OBJECT",
    )

    assert obj.validate() is True


def test_canonical_object_serializes():
    obj = CanonicalObject(
        object_id="OBJ-002",
        object_type="TEST_OBJECT",
        metadata={"source": "unit-test"},
    )

    data = obj.serialize()

    assert data["object_id"] == "OBJ-002"
    assert data["object_type"] == "TEST_OBJECT"
    assert data["version"] == "1.0"
    assert data["metadata"]["source"] == "unit-test"


def test_canonical_object_deserializes():
    data = {
        "object_id": "OBJ-003",
        "object_type": "TEST_OBJECT",
        "version": "1.1",
        "metadata": {"owner": "AI5R"},
    }

    obj = CanonicalObject.deserialize(data)

    assert obj.object_id == "OBJ-003"
    assert obj.object_type == "TEST_OBJECT"
    assert obj.version == "1.1"
    assert obj.metadata["owner"] == "AI5R"


def test_canonical_object_touch_updates_timestamp():
    obj = CanonicalObject(
        object_id="OBJ-004",
        object_type="TEST_OBJECT",
    )

    old_updated_at = obj.updated_at
    obj.touch()

    assert obj.updated_at >= old_updated_at


def test_canonical_object_generates_event():
    obj = CanonicalObject(
        object_id="OBJ-005",
        object_type="TEST_OBJECT",
        metadata={"domain": "foundation"},
    )

    event = obj.to_event("OBJECT_CREATED")

    assert event["event_type"] == "OBJECT_CREATED"
    assert event["object_id"] == "OBJ-005"
    assert event["object_type"] == "TEST_OBJECT"
    assert event["metadata"]["domain"] == "foundation"
    assert event["timestamp"].endswith("Z")


def test_canonical_object_auto_generates_identity():
    obj = CanonicalObject(
        object_type="KNW",
    )

    assert obj.object_id.startswith("AI5R-KNW-")
    assert CanonicalIdentityGenerator.current_counter("KNW") == 1


def test_canonical_object_keeps_manual_identity():
    obj = CanonicalObject(
        object_id="OBJ-MANUAL-001",
        object_type="TEST_OBJECT",
    )

    assert obj.object_id == "OBJ-MANUAL-001"
