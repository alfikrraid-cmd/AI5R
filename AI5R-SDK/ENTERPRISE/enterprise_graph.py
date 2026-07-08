from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enterprise import EnterpriseObject


@dataclass(slots=True)
class EnterpriseGraphRelationship:
    source_id: str
    target_id: str
    relationship_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class EnterpriseKnowledgeGraph:
    def __init__(self):
        self.nodes: dict[str, EnterpriseObject] = {}
        self.relationships: list[EnterpriseGraphRelationship] = []

    def add_node(self, node: EnterpriseObject) -> EnterpriseObject:
        self.nodes[node.object_id] = node
        return node

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> EnterpriseGraphRelationship:
        if source_id not in self.nodes:
            raise ValueError("source node does not exist")

        if target_id not in self.nodes:
            raise ValueError("target node does not exist")

        relationship = EnterpriseGraphRelationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            metadata=metadata or {},
        )

        self.relationships.append(relationship)
        return relationship

    def children(self, source_id: str) -> list[EnterpriseObject]:
        return [
            self.nodes[relationship.target_id]
            for relationship in self.relationships
            if relationship.source_id == source_id
        ]

    def parents(self, target_id: str) -> list[EnterpriseObject]:
        return [
            self.nodes[relationship.source_id]
            for relationship in self.relationships
            if relationship.target_id == target_id
        ]

    def neighbors(self, object_id: str) -> list[EnterpriseObject]:
        related_ids = []

        for relationship in self.relationships:
            if relationship.source_id == object_id:
                related_ids.append(relationship.target_id)

            if relationship.target_id == object_id:
                related_ids.append(relationship.source_id)

        return [
            self.nodes[related_id]
            for related_id in related_ids
            if related_id in self.nodes
        ]

    def find(self, object_id: str):
        return self.nodes.get(object_id)

    def find_by_type(self, object_type: str) -> list[EnterpriseObject]:
        return [
            node
            for node in self.nodes.values()
            if node.object_type == object_type
        ]

    def find_relationships(
        self,
        relationship_type: str | None = None,
    ) -> list[EnterpriseGraphRelationship]:
        if relationship_type is None:
            return list(self.relationships)

        return [
            relationship
            for relationship in self.relationships
            if relationship.relationship_type == relationship_type
        ]
