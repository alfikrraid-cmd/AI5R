from __future__ import annotations

from typing import Any, Callable


class ServiceContainer:
    """
    Lightweight Dependency Injection Container.

    Frozen Architecture compatible.
    """

    def __init__(self):
        self._factories: dict[str, Callable[[], Any]] = {}
        self._instances: dict[str, Any] = {}

    def register_instance(self, name: str, instance: Any) -> None:
        self._instances[name] = instance

    def register_factory(
        self,
        name: str,
        factory: Callable[[], Any],
    ) -> None:
        self._factories[name] = factory

    def resolve(self, name: str) -> Any:
        if name in self._instances:
            return self._instances[name]

        if name not in self._factories:
            raise KeyError(f"Service '{name}' is not registered")

        instance = self._factories[name]()
        self._instances[name] = instance
        return instance

    def registered_services(self) -> list[str]:
        return sorted(
            set(self._instances.keys()) |
            set(self._factories.keys())
        )
