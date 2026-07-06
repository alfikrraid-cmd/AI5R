from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SmokeTestResult:
    steps: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.failed) == 0


class RuntimeSmokeTest:
    def __init__(self):
        self.result = SmokeTestResult()

    def step(self, name: str, fn):
        try:
            fn()
            self.result.steps.append(name)
        except Exception:
            self.result.failed.append(name)
            raise

    def run(self, steps):
        for name, fn in steps:
            self.step(name, fn)

        return self.result
