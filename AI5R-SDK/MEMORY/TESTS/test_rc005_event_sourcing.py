from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from MEMORY.EVENT_SOURCING import EventStore


def test_event_append_and_get():
    store = EventStore()

    store.append("EMP-1", "CREATE", {"a": 1})
    store.append("EMP-1", "UPDATE", {"b": 2})

    events = store.get("EMP-1")

    assert len(events) == 2
    assert events[0].event_type == "CREATE"


def test_rebuild_state():
    store = EventStore()

    store.append("EMP-1", "CREATE", {"a": 1})
    store.append("EMP-1", "UPDATE", {"b": 2})

    state = store.rebuild("EMP-1")

    assert state == {"a": 1, "b": 2}
