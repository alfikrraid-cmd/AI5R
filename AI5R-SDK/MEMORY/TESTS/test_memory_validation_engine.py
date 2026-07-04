import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest

from MEMORY.memory_object import MemoryObject
from MEMORY.memory_validation_engine import MemoryValidationEngine


def test_memory_validation_success():

    memory = MemoryObject(
        memory_id="memory-001",
        learning_id="learning-001",
        confidence=0.90,
        digital_thread_id="thread-001",
    )

    validator = MemoryValidationEngine()

    assert validator.validate(memory) is True


def test_memory_validation_low_confidence():

    memory = MemoryObject(
        memory_id="memory-002",
        learning_id="learning-002",
        confidence=0.20,
        digital_thread_id="thread-002",
    )

    validator = MemoryValidationEngine()

    with pytest.raises(ValueError):
        validator.validate(memory)


def test_memory_validation_missing_thread():

    memory = MemoryObject(
        memory_id="memory-003",
        learning_id="learning-003",
        confidence=0.80,
        digital_thread_id="",
    )

    validator = MemoryValidationEngine()

    with pytest.raises(ValueError):
        validator.validate(memory)
