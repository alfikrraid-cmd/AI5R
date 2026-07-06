from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .employee_identity import EmployeeIdentity
from .employee_capability import EmployeeCapability


@dataclass(init=False)
class DigitalEmployee:
    identity: EmployeeIdentity
    capability: EmployeeCapability
    employee_id: str
    employee_name: str
    department: str
    role: str
    identity_id: str
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "ACTIVE"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __init__(self, *args, **kwargs):
        self.status = kwargs.pop("status", "ACTIVE")
        self.metadata = kwargs.pop("metadata", {})
        self.created_at = kwargs.pop(
            "created_at",
            datetime.now(timezone.utc).isoformat(),
        )

        if len(args) == 2 and isinstance(args[0], EmployeeIdentity):
            self.identity = args[0]
            self.capability = args[1]
            self.employee_id = self.identity.employee_id
            self.employee_name = self.identity.name
            self.department = self.identity.department
            self.role = self.identity.position
            self.identity_id = self.identity.employee_id
            self.capabilities = list(self.capability.capabilities)
            return

        self.employee_id = kwargs.pop("employee_id")
        self.employee_name = kwargs.pop("employee_name")
        self.department = kwargs.pop("department")
        self.role = kwargs.pop("role")
        self.identity_id = kwargs.pop("identity_id")
        self.capabilities = kwargs.pop("capabilities", [])

        self.identity = EmployeeIdentity(
            name=self.employee_name,
            organization=kwargs.pop("organization", "AI5R"),
            department=self.department,
            position=self.role,
        )

        self.capability = EmployeeCapability(
            capabilities=self.capabilities,
        )

    def add_capability(self, capability_id: str) -> None:
        if capability_id not in self.capabilities:
            self.capabilities.append(capability_id)

    def remove_capability(self, capability_id: str) -> None:
        if capability_id in self.capabilities:
            self.capabilities.remove(capability_id)

    def activate(self) -> None:
        self.status = "ACTIVE"

    def suspend(self) -> None:
        self.status = "SUSPENDED"
