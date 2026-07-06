from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Resource:
    resource_id: str
    resource_type: str
    owner_id: str
    status: str = "AVAILABLE"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ResourceManager:
    def __init__(self):
        self._resources: dict[str, Resource] = {}

    def register(
        self,
        resource_id: str,
        resource_type: str,
        owner_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Resource:
        if resource_id in self._resources:
            raise ValueError("resource already exists")

        resource = Resource(
            resource_id=resource_id,
            resource_type=resource_type,
            owner_id=owner_id,
            metadata=metadata or {},
        )

        self._resources[resource_id] = resource
        return resource

    def get(self, resource_id: str) -> Resource | None:
        return self._resources.get(resource_id)

    def list(self) -> list[Resource]:
        return list(self._resources.values())

    def list_by_owner(self, owner_id: str) -> list[Resource]:
        return [
            resource
            for resource in self._resources.values()
            if resource.owner_id == owner_id
        ]

    def allocate(self, resource_id: str) -> Resource:
        resource = self.get(resource_id)

        if resource is None:
            raise ValueError("resource not found")

        resource.status = "ALLOCATED"
        return resource

    def release(self, resource_id: str) -> Resource:
        resource = self.get(resource_id)

        if resource is None:
            raise ValueError("resource not found")

        resource.status = "AVAILABLE"
        return resource

    def unregister(self, resource_id: str) -> bool:
        if resource_id not in self._resources:
            return False

        del self._resources[resource_id]
        return True
