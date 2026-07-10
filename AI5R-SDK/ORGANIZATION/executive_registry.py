"""
AO-009
Executive Registry

Pure, dependency-free registry of AI executives keyed by executive_id.
Holds no business logic and no global state: each instance owns its own
storage. Deterministic insertion-ordered iteration.
"""

from __future__ import annotations

from typing import Any


class ExecutiveRegistry:
    def __init__(self) -> None:
        self._executives: dict[str, Any] = {}

    def register(self, executive: Any) -> Any:
        executive_id = executive.executive_id

        if executive_id in self._executives:
            raise ValueError(f"executive already registered: {executive_id}")

        self._executives[executive_id] = executive
        return executive

    def unregister(self, executive_id: str) -> None:
        if executive_id not in self._executives:
            raise KeyError(f"unknown executive_id: {executive_id}")

        del self._executives[executive_id]

    def get(self, executive_id: str) -> Any | None:
        return self._executives.get(executive_id)

    def get_by_department(self, department: str) -> list[Any]:
        return [
            executive
            for executive in self._executives.values()
            if executive.department == department
        ]

    def list_all(self) -> list[Any]:
        return list(self._executives.values())
