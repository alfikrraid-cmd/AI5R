from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class EmployeeMemory:
    employee_id: str
    memory_type: str
    content: Any
    memory_id: str = field(
        default_factory=lambda: f"MEM-{uuid4().hex[:12].upper()}"
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if not self.employee_id:
            raise ValueError("Employee ID is required")
        if not self.memory_type:
            raise ValueError("Memory type is required")
        if self.content is None:
            raise ValueError("Memory content is required")

    def snapshot(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "employee_id": self.employee_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }
