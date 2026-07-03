from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UniversalRelationship:
    """
    AX-005 Universal Relationship Contract
    Base relationship for all AI5R object connections.
    """

    id: str
    code: str
    type: str

    source_object_id: str
    target_object_id: str

    status: str = "active"
    version: str = "1.0.0"
    direction: str = "directed"

    weight: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    created_at: str | None = None
    updated_at: str | None = None

    thread_id: str | None = None
    policy_ids: list[str] = field(default_factory=list)

    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "type": self.type,
            "source_object_id": self.source_object_id,
            "target_object_id": self.target_object_id,
            "status": self.status,
            "version": self.version,
            "direction": self.direction,
            "weight": self.weight,
            "metadata": self.metadata,
            "properties": self.properties,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "thread_id": self.thread_id,
            "policy_ids": self.policy_ids,
            "checksum": self.checksum,
        }

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def set_property(self, key: str, value: Any) -> None:
        self.properties[key] = value

    def add_policy(self, policy_id: str) -> None:
        if policy_id not in self.policy_ids:
            self.policy_ids.append(policy_id)

    def deactivate(self) -> None:
        self.status = "inactive"

    def is_directed(self) -> bool:
        return self.direction == "directed"

    def is_bidirectional(self) -> bool:
        return self.direction == "bidirectional"
