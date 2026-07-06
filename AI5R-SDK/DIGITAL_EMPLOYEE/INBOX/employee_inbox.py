from __future__ import annotations

from collections import defaultdict
from typing import Any

from .employee_message import (
    EmployeeMessage,
    EmployeeMessagePriority,
    EmployeeMessageStatus,
)


class EmployeeInbox:
    def __init__(self) -> None:
        self._messages: dict[str, EmployeeMessage] = {}
        self._recipient_index: dict[str, list[str]] = defaultdict(list)

    def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        subject: str,
        body: str,
        priority: EmployeeMessagePriority | str = EmployeeMessagePriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> EmployeeMessage:
        message = EmployeeMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            subject=subject,
            body=body,
            priority=priority,
            metadata=metadata or {},
        )

        self._messages[message.message_id] = message
        self._recipient_index[recipient_id].append(message.message_id)
        return message

    def get_message(self, message_id: str) -> EmployeeMessage | None:
        return self._messages.get(message_id)

    def require_message(self, message_id: str) -> EmployeeMessage:
        message = self.get_message(message_id)
        if message is None:
            raise KeyError(f"Employee message not found: {message_id}")
        return message

    def list_messages(
        self,
        recipient_id: str,
        include_archived: bool = False,
    ) -> list[EmployeeMessage]:
        message_ids = self._recipient_index.get(recipient_id, [])

        messages = [
            self._messages[message_id]
            for message_id in message_ids
            if message_id in self._messages
        ]

        if include_archived:
            return list(messages)

        return [
            message
            for message in messages
            if message.status != EmployeeMessageStatus.ARCHIVED
        ]

    def list_unread(self, recipient_id: str) -> list[EmployeeMessage]:
        return [
            message
            for message in self.list_messages(recipient_id)
            if message.status == EmployeeMessageStatus.NEW
        ]

    def mark_read(self, message_id: str) -> EmployeeMessage:
        return self.require_message(message_id).mark_read()

    def archive(self, message_id: str) -> EmployeeMessage:
        return self.require_message(message_id).archive()

    def unread_count(self, recipient_id: str) -> int:
        return len(self.list_unread(recipient_id))

    def snapshot(self, recipient_id: str | None = None) -> dict[str, Any]:
        if recipient_id is not None:
            return {
                "recipient_id": recipient_id,
                "messages": [
                    message.snapshot()
                    for message in self.list_messages(
                        recipient_id=recipient_id,
                        include_archived=True,
                    )
                ],
                "unread_count": self.unread_count(recipient_id),
            }

        return {
            "messages": {
                message_id: message.snapshot()
                for message_id, message in self._messages.items()
            }
        }
