from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from MEMORY.PERSISTENCE import PersistentMemoryStore, MemoryIndex


def test_memory_write_and_latest():
    store = PersistentMemoryStore()

    r1 = store.write("EMP-1", {"a": 1})
    r2 = store.write("EMP-1", {"a": 2})

    assert store.latest("EMP-1") == r2
    assert r2.version == 2


def test_memory_history():
    store = PersistentMemoryStore()

    store.write("EMP-1", {"a": 1})
    store.write("EMP-1", {"a": 2})

    assert len(store.history("EMP-1")) == 2


def test_memory_index():
    idx = MemoryIndex()

    idx.add("EMP-1", "M1")
    idx.add("EMP-1", "M2")

    assert idx.search("EMP-1") == ["M1", "M2"]
