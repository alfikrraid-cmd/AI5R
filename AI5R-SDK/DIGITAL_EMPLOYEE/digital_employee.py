from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DigitalEmployee:
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
