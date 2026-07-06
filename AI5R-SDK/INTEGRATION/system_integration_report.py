from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IntegrationReport:
    executed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)

    def add_step(self, name: str) -> None:
        self.executed_steps.append(name)

    def add_failure(self, name: str) -> None:
        self.failed_steps.append(name)

    @property
    def success(self) -> bool:
        return len(self.failed_steps) == 0

    def snapshot(self):
        return {
            "success": self.success,
            "executed_steps": list(self.executed_steps),
            "failed_steps": list(self.failed_steps),
        }
