from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class BrainContext:
    context_type: str
    data: dict[str, Any]
    created_at: str = datetime.now(UTC).isoformat()


class RealtimeBrainConnector:

    def __init__(self):
        self.context_history = []


    def send_to_brain(
        self,
        observation: dict[str, Any]
    ):

        context = BrainContext(
            context_type="REALTIME_CONTEXT",
            data=observation
        )

        self.context_history.append(context)

        return {
            "status": "CONNECTED",
            "context_type": context.context_type
        }


    def get_context_count(self):

        return len(self.context_history)
