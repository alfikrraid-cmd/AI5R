from __future__ import annotations

from .employee_conversation import EmployeeConversation


class EmployeeConversationStore:
    def __init__(self) -> None:
        self._conversations: dict[str, EmployeeConversation] = {}
        self._employee_index: dict[str, list[str]] = {}

    def create(
        self,
        employee_id: str,
        title: str = "",
    ) -> EmployeeConversation:
        conversation = EmployeeConversation(
            employee_id=employee_id,
            title=title,
        )

        self._conversations[conversation.conversation_id] = conversation
        self._employee_index.setdefault(employee_id, []).append(
            conversation.conversation_id
        )

        return conversation

    def get(
        self,
        conversation_id: str,
    ) -> EmployeeConversation | None:
        return self._conversations.get(conversation_id)

    def require(
        self,
        conversation_id: str,
    ) -> EmployeeConversation:
        conversation = self.get(conversation_id)

        if conversation is None:
            raise KeyError(
                f"Conversation not found: {conversation_id}"
            )

        return conversation

    def list(
        self,
        employee_id: str,
    ) -> list[EmployeeConversation]:
        return [
            self._conversations[cid]
            for cid in self._employee_index.get(employee_id, [])
        ]

    def delete(
        self,
        conversation_id: str,
    ) -> bool:
        conversation = self._conversations.pop(
            conversation_id,
            None,
        )

        if conversation is None:
            return False

        self._employee_index[conversation.employee_id] = [
            cid
            for cid in self._employee_index.get(
                conversation.employee_id,
                [],
            )
            if cid != conversation_id
        ]

        return True

    def count(
        self,
        employee_id: str | None = None,
    ) -> int:
        if employee_id is None:
            return len(self._conversations)

        return len(self.list(employee_id))

    def snapshot(
        self,
        employee_id: str | None = None,
    ):
        if employee_id is None:
            return {
                cid: conversation.snapshot()
                for cid, conversation in self._conversations.items()
            }

        return [
            conversation.snapshot()
            for conversation in self.list(employee_id)
        ]
