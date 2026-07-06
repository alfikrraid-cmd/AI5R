import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import (
    PROCESS_COMPLETED,
    PROCESS_FAILED,
    PROCESS_READY,
    PROCESS_RUNNING,
    PROCESS_WAITING,
    ProcessManager,
)


def test_create_process():
    manager = ProcessManager()

    process = manager.create_process(
        name="Marketing Workflow",
        process_type="WORKFLOW",
        priority=1,
    )

    assert process.name == "Marketing Workflow"
    assert process.process_type == "WORKFLOW"
    assert process.priority == 1
    assert process.status == PROCESS_READY
    assert process.process_id.startswith("PRC-")


def test_process_lifecycle():
    manager = ProcessManager()

    process = manager.create_process(
        name="Employee Task",
        process_type="EMPLOYEE_TASK",
    )

    started = manager.start(process.process_id)
    assert started["status"] == PROCESS_RUNNING
    assert process.started_at is not None

    waiting = manager.wait(process.process_id)
    assert waiting["status"] == PROCESS_WAITING

    completed = manager.complete(process.process_id)
    assert completed["status"] == PROCESS_COMPLETED
    assert process.finished_at is not None


def test_failed_process():
    manager = ProcessManager()

    process = manager.create_process(
        name="Reasoning Job",
        process_type="REASONING",
    )

    result = manager.fail(
        process_id=process.process_id,
        error="reasoning timeout",
    )

    assert result["status"] == PROCESS_FAILED
    assert process.error == "reasoning timeout"
    assert process.finished_at is not None


def test_list_by_status():
    manager = ProcessManager()

    p1 = manager.create_process("A", "TASK")
    p2 = manager.create_process("B", "TASK")

    manager.start(p1.process_id)

    ready = manager.list_by_status(PROCESS_READY)
    running = manager.list_by_status(PROCESS_RUNNING)

    assert ready == [p2]
    assert running == [p1]


def test_parent_child_processes():
    manager = ProcessManager()

    parent = manager.create_process(
        name="Parent Workflow",
        process_type="WORKFLOW",
    )

    child = manager.create_process(
        name="Child Task",
        process_type="EMPLOYEE_TASK",
        parent_process_id=parent.process_id,
    )

    assert manager.children_of(parent.process_id) == [child]


def test_process_summary():
    manager = ProcessManager()

    p1 = manager.create_process("A", "TASK")
    p2 = manager.create_process("B", "TASK")
    p3 = manager.create_process("C", "TASK")

    manager.start(p1.process_id)
    manager.complete(p2.process_id)
    manager.fail(p3.process_id, "failed")

    summary = manager.summary()

    assert summary[PROCESS_READY] == 0
    assert summary[PROCESS_RUNNING] == 1
    assert summary[PROCESS_COMPLETED] == 1
    assert summary[PROCESS_FAILED] == 1


def test_unknown_process_raises_key_error():
    manager = ProcessManager()

    try:
        manager.start("missing")
        assert False
    except KeyError:
        pass
