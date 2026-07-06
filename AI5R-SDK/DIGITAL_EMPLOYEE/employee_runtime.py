from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .employee_identity import EmployeeIdentity
from .employee_capability import EmployeeCapability


@dataclass
class EmployeeRuntimeInput:
    identity: EmployeeIdentity
    capability: EmployeeCapability
    task: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmployeeRuntimeResult:
    employee_id: str
    capability_id: str
    task: str
    status: str = "EXECUTED"
    output: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EmployeeRuntime:
    def __init__(self):
        self.history: list[EmployeeRuntimeResult] = []

    def execute(
        self,
        runtime_input: EmployeeRuntimeInput,
    ) -> EmployeeRuntimeResult:
        if not runtime_input.task:
            raise ValueError("task is required")

        result = EmployeeRuntimeResult(
            employee_id=runtime_input.identity.employee_id,
            capability_id=runtime_input.capability.capability_id,
            task=runtime_input.task,
            output={
                "employee": runtime_input.identity,
                "capability": runtime_input.capability,
                "payload": runtime_input.payload,
            },
            metadata=runtime_input.metadata,
        )

        self.history.append(result)
        return result

    def list_history(self) -> list[EmployeeRuntimeResult]:
        return self.history
