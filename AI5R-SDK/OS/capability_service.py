from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Capability:
    capability_id: str
    identity_id: str
    capability_name: str
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CapabilityService:
    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    def register(
        self,
        capability_id: str,
        identity_id: str,
        capability_name: str,
        version: str = "1.0",
        metadata: dict[str, Any] | None = None,
    ) -> Capability:
        if capability_id in self._capabilities:
            raise ValueError("capability already exists")

        capability = Capability(
            capability_id=capability_id,
            identity_id=identity_id,
            capability_name=capability_name,
            version=version,
            metadata=metadata or {},
        )

        self._capabilities[capability_id] = capability
        return capability

    def get(self, capability_id: str) -> Capability | None:
        return self._capabilities.get(capability_id)

    def list(self) -> list[Capability]:
        return list(self._capabilities.values())

    def list_by_identity(self, identity_id: str) -> list[Capability]:
        return [
            capability
            for capability in self._capabilities.values()
            if capability.identity_id == identity_id
        ]

    def update_metadata(
        self,
        capability_id: str,
        metadata: dict[str, Any],
    ) -> Capability:
        capability = self.get(capability_id)

        if capability is None:
            raise ValueError("capability not found")

        capability.metadata.update(metadata)
        return capability

    def unregister(self, capability_id: str) -> bool:
        if capability_id not in self._capabilities:
            return False

        del self._capabilities[capability_id]
        return True
