from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EmployeeIdentity:
    employee_id: str
    employee_name: str
    department: str
    role: str
    identity_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        if self.identity_id is None:
            self.identity_id = self.employee_id


@dataclass
class EmployeeRuntimeResult:
    employee_id: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EmployeeRuntime:
    def __init__(self, identity: EmployeeIdentity):
        self.identity = identity
        self.history: list[EmployeeRuntimeResult] = []

    def execute(
        self,
        task: str,
        payload: dict[str, Any] | None = None,
    ) -> EmployeeRuntimeResult:
        if not task:
            raise ValueError("task is required")

        result = EmployeeRuntimeResult(
            employee_id=self.identity.employee_id,
            status="EXECUTED",
            output={
                "task": task,
                "payload": payload or {},
                "employee_name": self.identity.employee_name,
                "department": self.identity.department,
                "role": self.identity.role,
            },
        )

        self.history.append(result)
        return result

    def list_history(self) -> list[EmployeeRuntimeResult]:
        return self.history
