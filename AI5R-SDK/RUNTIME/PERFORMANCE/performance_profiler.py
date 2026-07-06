from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ProfileResult:
    module: str
    execution_time_ms: float


class PerformanceProfiler:
    def __init__(self):
        self.records: list[ProfileResult] = []

    def profile(self, module: str, fn):
        start = time.time()
        result = fn()
        end = time.time()

        self.records.append(
            ProfileResult(
                module=module,
                execution_time_ms=(end - start) * 1000,
            )
        )

        return result

    def slowest(self):
        if not self.records:
            return None

        return max(self.records, key=lambda x: x.execution_time_ms)

    def snapshot(self):
        return [
            {
                "module": r.module,
                "time_ms": r.execution_time_ms,
            }
            for r in self.records
        ]
