from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class EmployeePerformance:
    employee_id: str

    performance_id: str = field(
        default_factory=lambda: f"PERF-{uuid4().hex[:12].upper()}"
    )

    completed_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0
    score: float = 100.0

    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def __post_init__(self) -> None:
        if not self.employee_id:
            raise ValueError("Employee ID is required")

    def record_success(self) -> None:
        self.completed_tasks += 1
        self._recalculate()

    def record_failure(self) -> None:
        self.failed_tasks += 1
        self._recalculate()

    def _recalculate(self) -> None:
        total = self.completed_tasks + self.failed_tasks

        if total > 0:
            self.success_rate = (
                self.completed_tasks / total
            ) * 100

        self.score = max(
            0.0,
            min(
                100.0,
                self.success_rate,
            ),
        )

        self.updated_at = datetime.now(UTC).isoformat()

    def snapshot(self) -> dict[str, Any]:
        return {
            "performance_id": self.performance_id,
            "employee_id": self.employee_id,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "score": self.score,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
