from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Callable, List


@dataclass(frozen=True)
class BootTask:
    name: str
    action: Callable[[], None]


@dataclass(frozen=True)
class BootResult:
    started_at: str
    finished_at: str
    executed_tasks: List[str] = field(default_factory=list)


class KernelBootManager:
    """
    AI5R OS Kernel Boot Manager.

    Executes registered boot tasks sequentially.
    """

    def __init__(self):
        self._tasks: List[BootTask] = []

    def register(self, task: BootTask) -> None:
        self._tasks.append(task)

    def boot(self) -> BootResult:
        started = datetime.now(UTC).isoformat()

        executed = []

        for task in self._tasks:
            task.action()
            executed.append(task.name)

        finished = datetime.now(UTC).isoformat()

        return BootResult(
            started_at=started,
            finished_at=finished,
            executed_tasks=executed,
        )
