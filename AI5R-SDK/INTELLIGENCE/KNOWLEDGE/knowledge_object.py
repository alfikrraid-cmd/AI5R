from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class KnowledgeObject:
    knowledge_id: str
    summary: str
    facts: list[str] = field(default_factory=list)
    classification: dict[str, Any] = field(default_factory=dict)
    priority: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def validate(self) -> bool:
        if not self.knowledge_id:
            raise ValueError("knowledge_id is required")
        if not self.summary:
            raise ValueError("summary is required")
        return True

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeObject":
        if not data:
            raise ValueError("Knowledge object data is required")

        return cls(
            knowledge_id=data["knowledge_id"],
            summary=data["summary"],
            facts=data.get("facts", []),
            classification=data.get("classification", {}),
            priority=data.get("priority", {}),
            relationships=data.get("relationships", []),
            conflicts=data.get("conflicts", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat() + "Z"),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat() + "Z"),
        )

    def attach_classification(self, classification: dict[str, Any]) -> "KnowledgeObject":
        self.classification = classification
        self.touch()
        return self

    def attach_priority(self, priority: dict[str, Any]) -> "KnowledgeObject":
        self.priority = priority
        self.touch()
        return self

    def add_relationship(self, relationship: dict[str, Any]) -> "KnowledgeObject":
        self.relationships.append(relationship)
        self.touch()
        return self

    def add_conflict(self, conflict: dict[str, Any]) -> "KnowledgeObject":
        self.conflicts.append(conflict)
        self.touch()
        return self

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat() + "Z"
