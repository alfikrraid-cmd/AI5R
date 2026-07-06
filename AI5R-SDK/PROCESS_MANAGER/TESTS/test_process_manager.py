import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PROCESS_MANAGER import ProcessManager


def test_process_manager_spawns_process():
    manager = ProcessManager()

    process = manager.spawn(
        process_name="Digital Employee",
        payload={
            "role": "assistant",
        },
    )

    assert process.process_name == "DIGITAL_EMPLOYEE"
    assert process.status == "RUNNING"
    assert process.payload["role"] == "assistant"
    assert process.process_id is not None


def test_process_manager_gets_process():
    manager = ProcessManager()

    process = manager.spawn("Digital Employee")

    result = manager.get(process.process_id)

    assert result is process


def test_process_manager_lists_processes():
    manager = ProcessManager()

    manager.spawn("Digital Employee")
    manager.spawn("Digital School")

    result = manager.list()

    assert len(result) == 2


def test_process_manager_stops_process():
    manager = ProcessManager()

    process = manager.spawn("Digital Employee")

    stopped = manager.stop(process.process_id)

    assert stopped.status == "STOPPED"
    assert manager.status(process.process_id) == "STOPPED"


def test_process_manager_returns_none_for_unknown_process():
    manager = ProcessManager()

    assert manager.get("unknown") is None
    assert manager.stop("unknown") is None
    assert manager.status("unknown") is None


def test_process_manager_requires_name():
    manager = ProcessManager()

    try:
        manager.spawn("")
    except ValueError as error:
        assert str(error) == "process_name is required"
    else:
        raise AssertionError("Expected ValueError")
