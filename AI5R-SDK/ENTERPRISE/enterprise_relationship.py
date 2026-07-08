from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class EnterpriseRelationship:
    source_id: str
    target_id: str
    relationship_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class EnterpriseRelationshipGraph:
    def __init__(self):
        self.relationships: list[EnterpriseRelationship] = []

    def connect(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> EnterpriseRelationship:
        relationship = EnterpriseRelationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            metadata=metadata or {},
        )

        self.relationships.append(relationship)

        return relationship

    def children_of(self, source_id: str):
        return [
            relationship
            for relationship in self.relationships
            if relationship.source_id == source_id
        ]

    def parents_of(self, target_id: str):
        return [
            relationship
            for relationship in self.relationships
            if relationship.target_id == target_id
        ]

    def list_all(self):
        return list(self.relationships)
