from datetime import UTC, datetime, timedelta

import pytest

from MANUFACTURING_CENTER.manufacturing_schedule import (
    ManufacturingSchedule,
    ManufacturingSchedulePriority,
    ManufacturingScheduleStatus,
)


def make_schedule(**overrides: object) -> ManufacturingSchedule:
    now = datetime.now(UTC)

    defaults: dict[str, object] = {
        "schedule_id": "SCH-001",
        "plan_id": "PLAN-001",
        "queued_at": now,
        "scheduled_start": now + timedelta(minutes=5),
        "estimated_duration": 120.0,
        "priority": ManufacturingSchedulePriority.NORMAL,
        "status": ManufacturingScheduleStatus.QUEUED,
        "execution_levels": (
            ("REQUIREMENTS",),
            ("BACKEND", "FRONTEND"),
            ("INTEGRATION",),
        ),
        "resource_plan": {},
        "worker_assignment": {},
        "metadata": {"source": "ManufacturingScheduler"},
    }

    defaults.update(overrides)
    return ManufacturingSchedule(**defaults)  # type: ignore[arg-type]


def test_create_schedule() -> None:
    schedule = make_schedule()

    assert schedule.schedule_id == "SCH-001"
    assert schedule.plan_id == "PLAN-001"
    assert schedule.priority is ManufacturingSchedulePriority.NORMAL
    assert schedule.status is ManufacturingScheduleStatus.QUEUED
    assert schedule.level_count == 3
    assert schedule.max_parallelism == 2
    assert schedule.estimated_finish is not None


def test_schedule_id_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match="schedule_id"):
        make_schedule(schedule_id="   ")


def test_plan_id_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match="plan_id"):
        make_schedule(plan_id="")


def test_queued_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="queued_at must be timezone-aware",
    ):
        make_schedule(queued_at=datetime.now())


def test_scheduled_start_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="scheduled_start must be timezone-aware",
    ):
        make_schedule(scheduled_start=datetime.now())


def test_estimated_duration_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="estimated_duration must not be negative",
    ):
        make_schedule(estimated_duration=-1.0)


def test_scheduled_start_must_not_precede_queued_at() -> None:
    now = datetime.now(UTC)

    with pytest.raises(
        ValueError,
        match="scheduled_start must not be earlier than queued_at",
    ):
        make_schedule(
            queued_at=now,
            scheduled_start=now - timedelta(seconds=1),
        )


def test_start_schedule() -> None:
    schedule = make_schedule()

    schedule.start()

    assert schedule.status is ManufacturingScheduleStatus.RUNNING
    assert schedule.started_at is not None


def test_complete_schedule() -> None:
    schedule = make_schedule()
    schedule.start()
    schedule.complete()

    assert schedule.status is ManufacturingScheduleStatus.COMPLETED
    assert schedule.finished_at is not None
    assert schedule.is_terminal is True


def test_fail_schedule() -> None:
    schedule = make_schedule()
    schedule.start()
    schedule.fail("worker unavailable")

    assert schedule.status is ManufacturingScheduleStatus.FAILED
    assert schedule.finished_at is not None
    assert schedule.metadata["failure_reason"] == "worker unavailable"


def test_cancel_schedule() -> None:
    schedule = make_schedule()
    schedule.cancel("order withdrawn")

    assert schedule.status is ManufacturingScheduleStatus.CANCELLED
    assert schedule.finished_at is not None
    assert schedule.metadata["cancellation_reason"] == "order withdrawn"


def test_terminal_schedule_cannot_start_again() -> None:
    schedule = make_schedule()
    schedule.cancel("order withdrawn")

    with pytest.raises(ValueError, match="terminal"):
        schedule.start()


def test_summary() -> None:
    schedule = make_schedule()

    assert schedule.summary() == {
        "schedule_id": "SCH-001",
        "plan_id": "PLAN-001",
        "priority": "normal",
        "status": "queued",
        "level_count": 3,
        "max_parallelism": 2,
        "estimated_duration": 120.0,
        "estimated_finish": schedule.estimated_finish,
    }
