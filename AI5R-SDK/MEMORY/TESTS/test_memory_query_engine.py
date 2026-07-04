import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MEMORY.memory_object import MemoryObject
from MEMORY.memory_registry import MemoryRegistry
from MEMORY.memory_query_engine import MemoryQueryEngine


def build_registry():

    registry = MemoryRegistry()

    memory_1 = MemoryObject(
        memory_id="memory-001",
        learning_id="learning-001",
        content={"lesson": "Pump vibration issue"},
        confidence=0.90,
        digital_thread_id="thread-001",
    )

    memory_2 = MemoryObject(
        memory_id="memory-002",
        learning_id="learning-002",
        content={"lesson": "Motor temperature issue"},
        confidence=0.60,
        digital_thread_id="thread-002",
    )

    memory_3 = MemoryObject(
        memory_id="memory-003",
        learning_id="learning-003",
        content={"lesson": "Pump leak issue"},
        confidence=0.75,
        digital_thread_id="thread-001",
    )

    registry.register(memory_1)
    registry.register(memory_2)
    registry.register(memory_3)

    return registry


def test_query_by_learning_id():

    registry = build_registry()

    query = MemoryQueryEngine(registry)

    results = query.by_learning_id("learning-001")

    assert len(results) == 1

    assert results[0].memory_id == "memory-001"


def test_query_by_digital_thread_id():

    registry = build_registry()

    query = MemoryQueryEngine(registry)

    results = query.by_digital_thread_id("thread-001")

    assert len(results) == 2


def test_query_by_min_confidence():

    registry = build_registry()

    query = MemoryQueryEngine(registry)

    results = query.by_min_confidence(0.80)

    assert len(results) == 1

    assert results[0].confidence == 0.90


def test_combined_find():

    registry = build_registry()

    query = MemoryQueryEngine(registry)

    results = query.find(
        digital_thread_id="thread-001",
        minimum_confidence=0.80,
    )

    assert len(results) == 1

    assert results[0].memory_id == "memory-001"
