from dataclasses import dataclass
from typing import Any


@dataclass
class StudioCommand:
    command: str
    payload: dict[str, Any]


class StudioCommandAPI:
    def execute(
        self,
        command: StudioCommand,
    ) -> dict[str, Any]:

        return {
            "accepted": True,
            "command": command.command,
            "payload": command.payload,
        }
