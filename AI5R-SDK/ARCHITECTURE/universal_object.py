from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UniversalObject:
    """
    AX-004 Universal Object Contract
    Base object for all AI5R domain objects.
    """

    id: str
    code: str
    name: str
    type: str

    subtype: str | None = None
    version: str = "1.0.0"
    status: str = "active"

    owner: str | None = None
    organization_id: str | None = None

    created_at: str | None = None
    updated_at: str | None = None

    labels: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    relationships: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)

    thread_id: str | None = None
    parent_id: str | None = None
    source: str | None = None
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "type": self.type,
            "subtype": self.subtype,
            "version": self.version,
            "status": self.status,
            "owner": self.owner,
            "organization_id": self.organization_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "labels": self.labels,
            "tags": self.tags,
            "metadata": self.metadata,
            "properties": self.properties,
            "relationships": self.relationships,
            "policies": self.policies,
            "thread_id": self.thread_id,
            "parent_id": self.parent_id,
            "source": self.source,
            "checksum": self.checksum,
        }

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def add_label(self, label: str) -> None:
        if label not in self.labels:
            self.labels.append(label)

    def add_relationship(self, relationship_id: str) -> None:
        if relationship_id not in self.relationships:
            self.relationships.append(relationship_id)

    def add_policy(self, policy_id: str) -> None:
        if policy_id not in self.policies:
            self.policies.append(policy_id)

    def set_property(self, key: str, value: Any) -> None:
        self.properties[key] = value

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value
