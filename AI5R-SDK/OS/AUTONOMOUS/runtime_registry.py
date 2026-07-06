from __future__ import annotations

from .autonomous_runtime import AutonomousRuntime


class RuntimeRegistry:
    def __init__(self):
        self._runtimes: dict[str, AutonomousRuntime] = {}

    def create_runtime(
        self,
        runtime_id: str,
    ) -> AutonomousRuntime:

        runtime = AutonomousRuntime(runtime_id)

        self._runtimes[runtime_id] = runtime

        return runtime

    def get_runtime(
        self,
        runtime_id: str,
    ):
        return self._runtimes.get(runtime_id)

    def require_runtime(
        self,
        runtime_id: str,
    ):
        runtime = self.get_runtime(runtime_id)

        if runtime is None:
            raise KeyError(runtime_id)

        return runtime

    def list_runtimes(self):
        return list(self._runtimes.values())

    def snapshot(self):
        return {
            runtime.runtime_id: runtime.snapshot()
            for runtime in self._runtimes.values()
        }
