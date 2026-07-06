from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class EmployeeConversation:
    employee_id: str

    conversation_id: str = field(
        default_factory=lambda: f"CONV-{uuid4().hex[:12].upper()}"
    )

    title: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
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

    def add_message(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not role:
            raise ValueError("Role is required")

        if not content:
            raise ValueError("Content is required")

        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.messages.append(message)
        self.updated_at = datetime.now(UTC).isoformat()

        return message

    def snapshot(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "employee_id": self.employee_id,
            "title": self.title,
            "messages": list(self.messages),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
