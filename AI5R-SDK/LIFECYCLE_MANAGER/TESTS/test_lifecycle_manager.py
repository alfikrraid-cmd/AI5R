import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PROCESS_MANAGER import ProcessManager
from LIFECYCLE_MANAGER import LifecycleManager


def test_pause_resume_stop_process():
    manager = ProcessManager()
    lifecycle = LifecycleManager(manager)

    process = manager.spawn("Digital Employee")

    lifecycle.pause(process.process_id)
    assert process.status == "PAUSED"

    lifecycle.resume(process.process_id)
    assert process.status == "RUNNING"

    lifecycle.stop(process.process_id)
    assert process.status == "STOPPED"

    assert len(process.payload["lifecycle"]) == 3


def test_invalid_transition():
    manager = ProcessManager()
    lifecycle = LifecycleManager(manager)

    process = manager.spawn("Digital Employee")
    lifecycle.stop(process.process_id)

    try:
        lifecycle.resume(process.process_id)
    except ValueError as error:
        assert "Invalid lifecycle transition" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_unknown_process_returns_none():
    manager = ProcessManager()
    lifecycle = LifecycleManager(manager)

    assert lifecycle.pause("unknown") is None
    assert lifecycle.resume("unknown") is None
    assert lifecycle.stop("unknown") is None
