import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MEMORY.memory_object import MemoryObject


def test_memory_object():

    memory = MemoryObject(

        memory_id="memory-001",

        learning_id="learning-001",

        content={

            "lesson": "Bearing wear detected",

        },

        confidence=0.91,

        digital_thread_id="thread-001",

    )

    assert memory.status == "memorized"

    assert memory.memory_type == "enterprise_memory"

    assert memory.learning_id == "learning-001"

    assert memory.confidence == 0.91


def test_memory_to_dict():

    memory = MemoryObject(

        memory_id="memory-002",

        learning_id="learning-002",

    )

    data = memory.to_dict()

    assert data["memory_id"] == "memory-002"

    assert data["learning_id"] == "learning-002"

    assert data["status"] == "memorized"
