import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_object import CanonicalObject
from FOUNDATION.canonical_registry import CanonicalRegistry


class DummyObject(CanonicalObject):
    pass


def test_registry_registers_and_resolves_target():
    registry = CanonicalRegistry()

    registry.register(
        key="DUMMY_OBJECT",
        target=DummyObject,
        metadata={"layer": "foundation"},
    )

    resolved = registry.resolve("DUMMY_OBJECT")

    assert resolved is DummyObject


def test_registry_normalizes_keys():
    registry = CanonicalRegistry()

    registry.register("knowledge_object", DummyObject)

    assert registry.contains("KNOWLEDGE_OBJECT") is True
    assert registry.contains("knowledge_object") is True


def test_registry_get_entry_returns_metadata():
    registry = CanonicalRegistry()

    registry.register(
        key="TEST_OBJECT",
        target=DummyObject,
        metadata={"object_type": "TEST_OBJECT"},
    )

    entry = registry.get_entry("TEST_OBJECT")

    assert entry.key == "TEST_OBJECT"
    assert entry.target is DummyObject
    assert entry.metadata["object_type"] == "TEST_OBJECT"


def test_registry_unregisters_key():
    registry = CanonicalRegistry()

    registry.register("TEMP_OBJECT", DummyObject)
    assert registry.contains("TEMP_OBJECT") is True

    registry.unregister("TEMP_OBJECT")

    assert registry.contains("TEMP_OBJECT") is False


def test_registry_lists_keys_and_entries():
    registry = CanonicalRegistry()

    registry.register("A_OBJECT", DummyObject)
    registry.register("B_OBJECT", DummyObject)

    assert registry.keys() == ["A_OBJECT", "B_OBJECT"]
    assert len(registry.entries()) == 2


def test_registry_clear_removes_all_entries():
    registry = CanonicalRegistry()

    registry.register("A_OBJECT", DummyObject)
    registry.register("B_OBJECT", DummyObject)

    registry.clear()

    assert registry.keys() == []
    assert registry.entries() == []


def test_registry_raises_for_missing_key():
    registry = CanonicalRegistry()

    try:
        registry.resolve("MISSING_OBJECT")
        assert False
    except KeyError as error:
        assert "MISSING_OBJECT" in str(error)
