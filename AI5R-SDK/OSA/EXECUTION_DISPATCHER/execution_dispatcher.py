from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class ExecutionJob:
    execution_id: str
    assignment_id: str
    employee_id: str
    task_id: str
    status: ExecutionStatus = ExecutionStatus.CREATED
    result: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ExecutionDispatcher:

    def __init__(self):
        self.jobs: dict[str, ExecutionJob] = {}

    def dispatch(self, assignment):

        execution_id = f"EXE-{assignment.assignment_id}"

        job = ExecutionJob(
            execution_id=execution_id,
            assignment_id=assignment.assignment_id,
            employee_id=assignment.employee_id,
            task_id=assignment.task_id,
            status=ExecutionStatus.RUNNING,
        )

        self.jobs[execution_id] = job
        return job

    def complete(self, execution_id: str, result: dict[str, Any]):

        job = self.jobs[execution_id]
        job.status = ExecutionStatus.SUCCESS
        job.result = result
        job.updated_at = datetime.now(UTC).isoformat()

        return job

    def fail(self, execution_id: str, reason: str):

        job = self.jobs[execution_id]
        job.status = ExecutionStatus.FAILED
        job.result = {"reason": reason}
        job.updated_at = datetime.now(UTC).isoformat()

        return job
