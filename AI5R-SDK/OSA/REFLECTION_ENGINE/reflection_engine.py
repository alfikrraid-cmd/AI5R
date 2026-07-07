from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ReflectionStatus(str, Enum):
    CREATED = "CREATED"
    PASSED = "PASSED"
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"
    FAILED = "FAILED"


@dataclass
class ReflectionResult:
    reflection_id: str
    execution_id: str
    task_id: str
    employee_id: str
    status: ReflectionStatus
    score: float
    insights: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ReflectionEngine:
    def reflect(self, execution_job) -> ReflectionResult:
        if not execution_job.execution_id:
            raise ValueError("execution_id is required")

        score = self._score_execution(execution_job)
        status = self._determine_status(score)

        return ReflectionResult(
            reflection_id=f"REF-{execution_job.execution_id}",
            execution_id=execution_job.execution_id,
            task_id=execution_job.task_id,
            employee_id=execution_job.employee_id,
            status=status,
            score=score,
            insights=self._generate_insights(execution_job, score),
            metadata={
                "execution_status": str(execution_job.status),
                "result": execution_job.result,
            },
        )

    def _score_execution(self, execution_job) -> float:
        if str(execution_job.status).endswith("FAILED"):
            return 0.0

        if not execution_job.result:
            return 0.4

        if "output" in execution_job.result:
            return 1.0

        return 0.7

    def _determine_status(self, score: float) -> ReflectionStatus:
        if score >= 0.8:
            return ReflectionStatus.PASSED

        if score >= 0.4:
            return ReflectionStatus.NEEDS_IMPROVEMENT

        return ReflectionStatus.FAILED

    def _generate_insights(self, execution_job, score: float) -> list[str]:
        if score >= 0.8:
            return ["Execution produced a usable output"]

        if score >= 0.4:
            return ["Execution completed but output quality needs improvement"]

        return ["Execution failed or produced no usable result"]
