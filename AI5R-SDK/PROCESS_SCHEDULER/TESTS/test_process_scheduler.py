import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PROCESS_SCHEDULER import ProcessScheduler


def test_process_scheduler_schedules_process():
    scheduler = ProcessScheduler()

    scheduled = scheduler.schedule(
        process_id="p-001",
        process_name="Digital Employee",
        priority="HIGH",
        payload={"task": "assist"},
    )

    assert scheduled.process_id == "p-001"
    assert scheduled.process_name == "DIGITAL_EMPLOYEE"
    assert scheduled.priority == "HIGH"
    assert scheduled.status == "QUEUED"
    assert scheduled.payload["task"] == "assist"


def test_process_scheduler_orders_by_priority():
    scheduler = ProcessScheduler()

    scheduler.schedule("p-low", "Low Process", priority="LOW")
    scheduler.schedule("p-high", "High Process", priority="HIGH")
    scheduler.schedule("p-medium", "Medium Process", priority="MEDIUM")

    first = scheduler.next()
    second = scheduler.next()
    third = scheduler.next()

    assert first.process_id == "p-high"
    assert second.process_id == "p-medium"
    assert third.process_id == "p-low"


def test_process_scheduler_dispatches_next_process():
    scheduler = ProcessScheduler()

    scheduler.schedule("p-001", "Digital Employee")

    scheduled = scheduler.next()

    assert scheduled.status == "DISPATCHED"
    assert scheduler.next() is None


def test_process_scheduler_cancels_process():
    scheduler = ProcessScheduler()

    scheduled = scheduler.schedule("p-001", "Digital Employee")

    cancelled = scheduler.cancel(scheduled.schedule_id)

    assert cancelled.status == "CANCELLED"
    assert scheduler.queue() == []


def test_process_scheduler_requires_valid_input():
    scheduler = ProcessScheduler()

    try:
        scheduler.schedule("", "Digital Employee")
    except ValueError as error:
        assert str(error) == "process_id is required"
    else:
        raise AssertionError("Expected ValueError")

    try:
        scheduler.schedule("p-001", "")
    except ValueError as error:
        assert str(error) == "process_name is required"
    else:
        raise AssertionError("Expected ValueError")

    try:
        scheduler.schedule("p-001", "Digital Employee", priority="URGENT")
    except ValueError as error:
        assert str(error) == "priority must be HIGH, MEDIUM, or LOW"
    else:
        raise AssertionError("Expected ValueError")
