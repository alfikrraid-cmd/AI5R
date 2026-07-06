from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


PROCESS_READY = "READY"
PROCESS_RUNNING = "RUNNING"
PROCESS_WAITING = "WAITING"
PROCESS_COMPLETED = "COMPLETED"
PROCESS_FAILED = "FAILED"


@dataclass
class OSProcess:
    name: str
    process_type: str
    priority: int = 5
    parent_process_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = PROCESS_READY
    process_id: str = field(default_factory=lambda: f"PRC-{uuid4()}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class ProcessManager:
    """
    AI5R OS Process Manager.

    Manages lifecycle of OS-level processes without changing
    existing public contracts.
    """

    def __init__(self):
        self._processes: dict[str, OSProcess] = {}

    def create_process(
        self,
        name: str,
        process_type: str,
        priority: int = 5,
        parent_process_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OSProcess:
        process = OSProcess(
            name=name,
            process_type=process_type,
            priority=priority,
            parent_process_id=parent_process_id,
            metadata=metadata or {},
        )

        self._processes[process.process_id] = process
        return process

    def start(self, process_id: str) -> dict[str, Any]:
        process = self._get(process_id)

        process.status = PROCESS_RUNNING
        process.started_at = datetime.now(UTC).isoformat()

        return {
            "status": PROCESS_RUNNING,
            "process": process,
        }

    def wait(self, process_id: str) -> dict[str, Any]:
        process = self._get(process_id)

        process.status = PROCESS_WAITING

        return {
            "status": PROCESS_WAITING,
            "process": process,
        }

    def complete(self, process_id: str) -> dict[str, Any]:
        process = self._get(process_id)

        process.status = PROCESS_COMPLETED
        process.finished_at = datetime.now(UTC).isoformat()

        return {
            "status": PROCESS_COMPLETED,
            "process": process,
        }

    def fail(
        self,
        process_id: str,
        error: str,
    ) -> dict[str, Any]:
        process = self._get(process_id)

        process.status = PROCESS_FAILED
        process.error = error
        process.finished_at = datetime.now(UTC).isoformat()

        return {
            "status": PROCESS_FAILED,
            "process": process,
        }

    def get(self, process_id: str) -> OSProcess | None:
        return self._processes.get(process_id)

    def list_all(self) -> list[OSProcess]:
        return sorted(
            self._processes.values(),
            key=lambda process: (
                process.priority,
                process.created_at,
            ),
        )

    def list_by_status(self, status: str) -> list[OSProcess]:
        return [
            process
            for process in self.list_all()
            if process.status == status
        ]

    def children_of(self, parent_process_id: str) -> list[OSProcess]:
        return [
            process
            for process in self.list_all()
            if process.parent_process_id == parent_process_id
        ]

    def summary(self) -> dict[str, int]:
        result = {
            PROCESS_READY: 0,
            PROCESS_RUNNING: 0,
            PROCESS_WAITING: 0,
            PROCESS_COMPLETED: 0,
            PROCESS_FAILED: 0,
        }

        for process in self._processes.values():
            result[process.status] = result.get(process.status, 0) + 1

        return result

    def _get(self, process_id: str) -> OSProcess:
        process = self.get(process_id)

        if process is None:
            raise KeyError(f"Process '{process_id}' is not registered")

        return process
