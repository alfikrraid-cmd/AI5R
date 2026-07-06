from DIGITAL_EMPLOYEE.COLLABORATION import (
    CollaborationManager,
    CollaborationStatus,
)


def test_create_task():
    manager = CollaborationManager()

    task = manager.create_task(
        owner_employee_id="EMP-001",
        assigned_employee_id="EMP-002",
        title="Prepare report",
    )

    assert task.title == "Prepare report"
    assert task.status == CollaborationStatus.CREATED


def test_update_status():
    manager = CollaborationManager()

    task = manager.create_task(
        "EMP-001",
        "EMP-002",
        "Task",
    )

    manager.update_status(
        task.task_id,
        "IN_PROGRESS",
    )

    assert task.status == CollaborationStatus.IN_PROGRESS


def test_list_tasks():
    manager = CollaborationManager()

    manager.create_task(
        "EMP-001",
        "EMP-002",
        "Task A",
    )

    manager.create_task(
        "EMP-003",
        "EMP-001",
        "Task B",
    )

    assert len(manager.list_tasks("EMP-001")) == 2


def test_snapshot():
    manager = CollaborationManager()

    task = manager.create_task(
        "EMP-001",
        "EMP-002",
        "Task",
    )

    snapshot = manager.snapshot()

    assert task.task_id in snapshot


def test_missing_task():
    manager = CollaborationManager()

    try:
        manager.require_task("UNKNOWN")
    except KeyError:
        pass
    else:
        raise AssertionError
