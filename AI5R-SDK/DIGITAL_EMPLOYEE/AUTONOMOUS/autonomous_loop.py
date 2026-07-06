from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Callable, Any


class AutonomousState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass
class AutonomousLoop:
    employee_id: str

    state: AutonomousState = AutonomousState.IDLE

    iteration: int = 0

    last_result: Any = None

    started_at: str | None = None
    stopped_at: str | None = None

    history: list[dict[str, Any]] = field(default_factory=list)

    def start(self) -> None:
        self.state = AutonomousState.RUNNING
        self.started_at = datetime.now(UTC).isoformat()

    def stop(self) -> None:
        self.state = AutonomousState.STOPPED
        self.stopped_at = datetime.now(UTC).isoformat()

    def step(
        self,
        worker: Callable[[], Any],
    ) -> Any:

        if self.state != AutonomousState.RUNNING:
            raise RuntimeError("Autonomous loop is not running")

        try:
            result = worker()

            self.iteration += 1
            self.last_result = result

            self.history.append(
                {
                    "iteration": self.iteration,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "result": result,
                }
            )

            return result

        except Exception:
            self.state = AutonomousState.FAILED
            raise

    def snapshot(self) -> dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "state": self.state.value,
            "iteration": self.iteration,
            "last_result": self.last_result,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "history": list(self.history),
        }
