from __future__ import annotations

from typing import Any


class RuntimeRegistry:
    """
    Central registry for all AI5R runtime objects.

    Stores runtime instances without modifying any existing public
    contracts.
    """

    def __init__(self):
        self._registry: dict[str, Any] = {}

    def register(
        self,
        runtime_id: str,
        runtime: Any,
    ) -> None:
        self._registry[runtime_id] = runtime

    def unregister(
        self,
        runtime_id: str,
    ) -> Any | None:
        return self._registry.pop(runtime_id, None)

    def get(
        self,
        runtime_id: str,
    ) -> Any | None:
        return self._registry.get(runtime_id)

    def exists(
        self,
        runtime_id: str,
    ) -> bool:
        return runtime_id in self._registry

    def list_ids(self) -> list[str]:
        return sorted(self._registry.keys())

    def list_all(self) -> list[Any]:
        return [
            self._registry[key]
            for key in self.list_ids()
        ]

    def count(self) -> int:
        return len(self._registry)

    def clear(self) -> None:
        self._registry.clear()
