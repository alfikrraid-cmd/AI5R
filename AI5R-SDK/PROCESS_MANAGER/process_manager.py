from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4


@dataclass
class DigitalProcess:
    process_name: str
    process_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    process_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "CREATED"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProcessManager:
    def __init__(self):
        self._processes = {}

    def spawn(self, process_name: str, process_type: str = "DIGITAL_PROCESS", payload=None):
        if not process_name or not process_name.strip():
            raise ValueError("process_name is required")

        process = DigitalProcess(
            process_name=process_name.strip().upper().replace(" ", "_").replace("-", "_"),
            process_type=process_type,
            payload=payload or {},
            status="RUNNING",
        )

        self._processes[process.process_id] = process

        return process

    def get(self, process_id: str):
        return self._processes.get(process_id)

    def list(self):
        return list(self._processes.values())

    def stop(self, process_id: str):
        process = self.get(process_id)

        if process is None:
            return None

        process.status = "STOPPED"
        return process

    def status(self, process_id: str):
        process = self.get(process_id)

        if process is None:
            return None

        return process.status
