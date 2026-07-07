from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class CoordinationStatus(str, Enum):
    CREATED = "CREATED"
    COORDINATED = "COORDINATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class AgentWorkUnit:
    work_unit_id: str
    task_id: str
    employee_id: str
    capability_id: str
    instruction: str
    status: CoordinationStatus = CoordinationStatus.CREATED
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinationResult:
    coordination_id: str
    goal_id: str
    status: CoordinationStatus
    work_units: list[AgentWorkUnit] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class MultiAgentCoordinator:
    def coordinate(
        self,
        goal_id: str,
        assignments: list[Any],
    ) -> CoordinationResult:
        if not goal_id:
            raise ValueError("goal_id is required")

        if not assignments:
            raise ValueError("assignments are required")

        work_units = []

        for index, assignment in enumerate(assignments, start=1):
            work_units.append(
                AgentWorkUnit(
                    work_unit_id=f"WU-{goal_id}-{index:03d}",
                    task_id=assignment.task_id,
                    employee_id=assignment.employee_id,
                    capability_id=assignment.capability_id,
                    instruction=f"Execute task {assignment.task_id}",
                    status=CoordinationStatus.COORDINATED,
                )
            )

        return CoordinationResult(
            coordination_id=f"COORD-{goal_id}",
            goal_id=goal_id,
            status=CoordinationStatus.COORDINATED,
            work_units=work_units,
            summary={
                "work_unit_count": len(work_units),
                "employees": sorted(
                    {
                        work_unit.employee_id
                        for work_unit in work_units
                    }
                ),
            },
        )

    def complete(
        self,
        coordination_result: CoordinationResult,
        results: dict[str, dict[str, Any]],
    ) -> CoordinationResult:
        for work_unit in coordination_result.work_units:
            work_unit.result = results.get(work_unit.work_unit_id, {})
            work_unit.status = CoordinationStatus.COMPLETED

        coordination_result.status = CoordinationStatus.COMPLETED
        coordination_result.summary["completed_count"] = len(
            coordination_result.work_units
        )

        return coordination_result

    def fail(
        self,
        coordination_result: CoordinationResult,
        reason: str,
    ) -> CoordinationResult:
        coordination_result.status = CoordinationStatus.FAILED
        coordination_result.summary["reason"] = reason
        return coordination_result
