from DIGITAL_ORGANIZATION.message import Message


class CommunicationRuntime:

    def __init__(self):
        self._messages = []

    def send(
        self,
        sender: str,
        receiver: str,
        content: str,
        message_type: str = "TASK",
    ):
        message = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
        )

        self._messages.append(message)

        return {
            "status": "SENT",
            "message": message,
        }

    def inbox(self, receiver: str):
        return [
            message
            for message in self._messages
            if message.receiver == receiver
        ]

    def outbox(self, sender: str):
        return [
            message
            for message in self._messages
            if message.sender == sender
        ]

    def mark_completed(self, message_id: str):
        for message in self._messages:
            if message.message_id == message_id:
                message.status = "COMPLETED"
                return {
                    "status": "COMPLETED",
                    "message": message,
                }

        return {
            "status": "NOT_FOUND",
            "message": None,
        }
