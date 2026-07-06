from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class EmployeeMessageStatus(str, Enum):
    NEW = "NEW"
    READ = "READ"
    ARCHIVED = "ARCHIVED"


class EmployeeMessagePriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


@dataclass
class EmployeeMessage:
    sender_id: str
    recipient_id: str
    subject: str
    body: str
    message_id: str = field(default_factory=lambda: f"MSG-{uuid4().hex[:12].upper()}")
    priority: EmployeeMessagePriority = EmployeeMessagePriority.NORMAL
    status: EmployeeMessageStatus = EmployeeMessageStatus.NEW
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    read_at: str | None = None
    archived_at: str | None = None

    def __post_init__(self) -> None:
        if not self.sender_id:
            raise ValueError("Sender ID is required")
        if not self.recipient_id:
            raise ValueError("Recipient ID is required")
        if not self.subject:
            raise ValueError("Message subject is required")
        if not self.body:
            raise ValueError("Message body is required")

        if isinstance(self.priority, str):
            self.priority = EmployeeMessagePriority(self.priority)

        if isinstance(self.status, str):
            self.status = EmployeeMessageStatus(self.status)

    def mark_read(self) -> "EmployeeMessage":
        self.status = EmployeeMessageStatus.READ
        self.read_at = datetime.now(UTC).isoformat()
        return self

    def archive(self) -> "EmployeeMessage":
        self.status = EmployeeMessageStatus.ARCHIVED
        self.archived_at = datetime.now(UTC).isoformat()
        return self

    def snapshot(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "subject": self.subject,
            "body": self.body,
            "priority": self.priority.value,
            "status": self.status.value,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "read_at": self.read_at,
            "archived_at": self.archived_at,
        }
