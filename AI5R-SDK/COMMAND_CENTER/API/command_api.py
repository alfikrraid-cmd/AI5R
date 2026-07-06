from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class APIResponse:
    status: str
    data: dict[str, Any]
    created_at: str = datetime.now(UTC).isoformat()


class AI5RCommandAPI:

    def __init__(self):
        self.requests = []


    def health(self):

        return APIResponse(
            status="ONLINE",
            data={
                "system": "AI5R",
                "service": "COMMAND_CENTER"
            }
        )


    def send_command(
        self,
        command: dict[str, Any]
    ):

        self.requests.append(command)

        return APIResponse(
            status="ACCEPTED",
            data={
                "command": command,
                "queue_size": len(self.requests)
            }
        )
