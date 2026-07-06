from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Capability:
    capability_id: str
    capability_type: str
    implementation: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class CapabilityLoader:
    """
    AI5R OS Capability Loader.

    Registers capabilities into the OS runtime without changing
    existing frozen contracts.
    """

    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    def register(
        self,
        capability_id: str,
        capability_type: str,
        implementation: Any,
        metadata: dict[str, Any] | None = None,
    ) -> Capability:
        capability = Capability(
            capability_id=capability_id,
            capability_type=capability_type,
            implementation=implementation,
            metadata=metadata or {},
        )

        self._capabilities[capability_id] = capability
        return capability

    def get(
        self,
        capability_id: str,
    ) -> Capability | None:
        return self._capabilities.get(capability_id)

    def enable(
        self,
        capability_id: str,
    ):
        self._capabilities[capability_id].enabled = True

    def disable(
        self,
        capability_id: str,
    ):
        self._capabilities[capability_id].enabled = False

    def list_all(self) -> list[Capability]:
        return [
            self._capabilities[key]
            for key in sorted(self._capabilities)
        ]

    def list_enabled(self) -> list[Capability]:
        return [
            capability
            for capability in self.list_all()
            if capability.enabled
        ]

    def list_by_type(
        self,
        capability_type: str,
    ) -> list[Capability]:
        return [
            capability
            for capability in self.list_all()
            if capability.capability_type == capability_type
        ]

    def summary(self):
        return {
            "registered": len(self._capabilities),
            "enabled": len(self.list_enabled()),
            "disabled": len(self._capabilities) - len(self.list_enabled()),
        }
