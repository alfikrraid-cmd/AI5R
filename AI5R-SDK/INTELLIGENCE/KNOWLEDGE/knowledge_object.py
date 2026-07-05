from typing import Any

from FOUNDATION.canonical_object import CanonicalObject, utc_now_iso


class KnowledgeObject(CanonicalObject):
    def __init__(
        self,
        knowledge_id: str | None = None,
        summary: str = "",
        facts: list[str] | None = None,
        classification: dict[str, Any] | None = None,
        priority: dict[str, Any] | None = None,
        relationships: list[dict[str, Any]] | None = None,
        conflicts: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
        version: str = "1.0",
    ):
        super().__init__(
            object_type="KNOWLEDGE_OBJECT",
            object_id=knowledge_id,
            version=version,
            metadata=metadata or {},
            created_at=created_at or utc_now_iso(),
            updated_at=updated_at or utc_now_iso(),
        )

        self.summary = summary
        self.facts = facts or []
        self.classification = classification or {}
        self.priority = priority or {}
        self.relationships = relationships or []
        self.conflicts = conflicts or []

        # scoring signals (native state)
        self.impact = metadata.get("impact") if metadata else None
        self.urgency = metadata.get("urgency") if metadata else None
        self.actionability = metadata.get("actionability") if metadata else None


    @property
    def knowledge_id(self) -> str:
        return self.object_id

    def validate(self) -> bool:
        super().validate()

        if not self.summary:
            raise ValueError("summary is required")

        return True

    def to_dict(self) -> dict[str, Any]:
        self.validate()

        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "knowledge_id": self.knowledge_id,
            "summary": self.summary,
            "facts": self.facts,
            "classification": self.classification,
            "priority": self.priority,
            "relationships": self.relationships,
            "conflicts": self.conflicts,
            "metadata": self.metadata,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def serialize(self) -> dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeObject":
        if not data:
            raise ValueError("Knowledge object data is required")

        metadata = dict(data.get("metadata", {}))

        for key in ["impact", "urgency", "actionability"]:
            if key in data:
                metadata[key] = data[key]

        obj = cls(
            knowledge_id=data.get("knowledge_id") or data.get("object_id"),
            summary=data["summary"],
            facts=data.get("facts", []),
            classification=data.get("classification", {}),
            priority=data.get("priority", {}),
            relationships=data.get("relationships", []),
            conflicts=data.get("conflicts", []),
            metadata=metadata,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            version=data.get("version", "1.0"),
        )

        obj.impact = metadata.get("impact")
        obj.urgency = metadata.get("urgency")
        obj.actionability = metadata.get("actionability")

        return obj

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "KnowledgeObject":
        return cls.from_dict(data)

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
