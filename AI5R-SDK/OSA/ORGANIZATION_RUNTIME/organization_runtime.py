from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class OrganizationRuntimeStatus(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class OrganizationRuntimeResult:
    runtime_id: str
    goal_id: str
    status: OrganizationRuntimeStatus
    coordination_id: str
    work_unit_count: int
    summary: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class OrganizationRuntime:
    def start(self, goal_id: str, coordination_result) -> OrganizationRuntimeResult:
        if not goal_id:
            raise ValueError("goal_id is required")

        if not coordination_result:
            raise ValueError("coordination_result is required")

        return OrganizationRuntimeResult(
            runtime_id=f"ORG-RUN-{goal_id}",
            goal_id=goal_id,
            status=OrganizationRuntimeStatus.ACTIVE,
            coordination_id=coordination_result.coordination_id,
            work_unit_count=len(coordination_result.work_units),
            summary={
                "coordination_status": str(coordination_result.status),
                "employees": coordination_result.summary.get("employees", []),
            },
        )

    def complete(self, runtime_result: OrganizationRuntimeResult) -> OrganizationRuntimeResult:
        runtime_result.status = OrganizationRuntimeStatus.COMPLETED
        runtime_result.summary["completed"] = True
        return runtime_result

    def fail(
        self,
        runtime_result: OrganizationRuntimeResult,
        reason: str,
    ) -> OrganizationRuntimeResult:
        runtime_result.status = OrganizationRuntimeStatus.FAILED
        runtime_result.summary["reason"] = reason
        return runtime_result
