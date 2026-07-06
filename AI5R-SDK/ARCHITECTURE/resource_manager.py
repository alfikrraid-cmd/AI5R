from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Resource:
    resource_id: str
    resource_type: str
    resource: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    allocated: bool = False
    allocated_at: str | None = None
    released_at: str | None = None


class ResourceManager:
    """
    AI5R OS Resource Manager.

    Responsible for lifecycle management of runtime resources.
    """

    def __init__(self):
        self._resources: dict[str, Resource] = {}

    def register(
        self,
        resource_id: str,
        resource_type: str,
        resource: Any,
        metadata: dict[str, Any] | None = None,
    ) -> Resource:
        obj = Resource(
            resource_id=resource_id,
            resource_type=resource_type,
            resource=resource,
            metadata=metadata or {},
        )

        self._resources[resource_id] = obj
        return obj

    def allocate(self, resource_id: str) -> Resource:
        resource = self._resources[resource_id]

        resource.allocated = True
        resource.allocated_at = datetime.now(UTC).isoformat()

        return resource

    def release(self, resource_id: str) -> Resource:
        resource = self._resources[resource_id]

        resource.allocated = False
        resource.released_at = datetime.now(UTC).isoformat()

        return resource

    def get(self, resource_id: str) -> Resource | None:
        return self._resources.get(resource_id)

    def list_all(self) -> list[Resource]:
        return [
            self._resources[key]
            for key in sorted(self._resources)
        ]

    def allocated(self) -> list[Resource]:
        return [
            resource
            for resource in self.list_all()
            if resource.allocated
        ]

    def summary(self):
        return {
            "registered": len(self._resources),
            "allocated": len(self.allocated()),
            "available": len(self._resources) - len(self.allocated()),
        }
