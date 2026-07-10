from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum, unique
from typing import Any


@unique
class ManufacturingSchedulePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@unique
class ManufacturingScheduleStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            self.COMPLETED,
            self.FAILED,
            self.CANCELLED,
        }


@dataclass(slots=True, kw_only=True)
class ManufacturingSchedule:
    schedule_id: str
    plan_id: str
    queued_at: datetime
    scheduled_start: datetime
    estimated_duration: float
    priority: ManufacturingSchedulePriority
    status: ManufacturingScheduleStatus
    execution_levels: tuple[tuple[str, ...], ...]
    resource_plan: dict[str, Any] = field(default_factory=dict)
    worker_assignment: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schedule_id = self.schedule_id.strip()
        self.plan_id = self.plan_id.strip()

        if not self.schedule_id:
            raise ValueError("schedule_id must not be empty")

        if not self.plan_id:
            raise ValueError("plan_id must not be empty")

        if self.queued_at.tzinfo is None:
            raise ValueError("queued_at must be timezone-aware")

        if self.scheduled_start.tzinfo is None:
            raise ValueError("scheduled_start must be timezone-aware")

        if self.started_at is not None and self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")

        if self.finished_at is not None and self.finished_at.tzinfo is None:
            raise ValueError("finished_at must be timezone-aware")

        if self.estimated_duration < 0:
            raise ValueError(
                "estimated_duration must not be negative"
            )

        if self.scheduled_start < self.queued_at:
            raise ValueError(
                "scheduled_start must not be earlier than queued_at"
            )

        self.execution_levels = tuple(
            tuple(level)
            for level in self.execution_levels
        )
        self.resource_plan = dict(self.resource_plan)
        self.worker_assignment = dict(self.worker_assignment)
        self.metadata = dict(self.metadata)

    @property
    def estimated_finish(self) -> datetime:
        return self.scheduled_start + timedelta(
            seconds=self.estimated_duration
        )

    @property
    def level_count(self) -> int:
        return len(self.execution_levels)

    @property
    def max_parallelism(self) -> int:
        return max(
            (len(level) for level in self.execution_levels),
            default=0,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    def start(self) -> None:
        if self.is_terminal:
            raise ValueError("terminal schedule cannot be started")

        if self.status is not ManufacturingScheduleStatus.QUEUED:
            raise ValueError(
                "schedule can only start from queued status"
            )

        self.status = ManufacturingScheduleStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        if self.is_terminal:
            raise ValueError(
                "terminal schedule cannot be completed"
            )

        if self.status is not ManufacturingScheduleStatus.RUNNING:
            raise ValueError(
                "schedule must be running before completion"
            )

        self.status = ManufacturingScheduleStatus.COMPLETED
        self.finished_at = datetime.now(UTC)

    def fail(self, reason: str) -> None:
        reason = reason.strip()

        if not reason:
            raise ValueError("reason must not be empty")

        if self.is_terminal:
            raise ValueError("terminal schedule cannot fail")

        if self.status is not ManufacturingScheduleStatus.RUNNING:
            raise ValueError(
                "schedule must be running before failure"
            )

        self.status = ManufacturingScheduleStatus.FAILED
        self.finished_at = datetime.now(UTC)
        self.metadata["failure_reason"] = reason

    def cancel(self, reason: str) -> None:
        reason = reason.strip()

        if not reason:
            raise ValueError("reason must not be empty")

        if self.is_terminal:
            raise ValueError("terminal schedule cannot be cancelled")

        self.status = ManufacturingScheduleStatus.CANCELLED
        self.finished_at = datetime.now(UTC)
        self.metadata["cancellation_reason"] = reason

    def summary(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "plan_id": self.plan_id,
            "priority": self.priority.value,
            "status": self.status.value,
            "level_count": self.level_count,
            "max_parallelism": self.max_parallelism,
            "estimated_duration": self.estimated_duration,
            "estimated_finish": self.estimated_finish,
        }
