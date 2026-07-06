from __future__ import annotations

from .autonomous_loop import AutonomousLoop


class AutonomousRuntime:
    def __init__(self):
        self._loops: dict[str, AutonomousLoop] = {}

    def create(
        self,
        employee_id: str,
    ) -> AutonomousLoop:

        loop = AutonomousLoop(
            employee_id=employee_id,
        )

        self._loops[employee_id] = loop

        return loop

    def get(
        self,
        employee_id: str,
    ) -> AutonomousLoop | None:
        return self._loops.get(employee_id)

    def require(
        self,
        employee_id: str,
    ) -> AutonomousLoop:

        loop = self.get(employee_id)

        if loop is None:
            raise KeyError(employee_id)

        return loop

    def snapshot(self):
        return {
            employee_id: loop.snapshot()
            for employee_id, loop
            in self._loops.items()
        }
