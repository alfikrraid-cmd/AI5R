from dataclasses import dataclass, field, asdict
from typing import Any
from FOUNDATION.canonical_object import utc_now_iso


@dataclass
class CanonicalEvent:
    event_id: str
    event_type: str
    source_object_id: str
    source_object_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    target_object_id: str | None = None
    target_object_type: str | None = None
    version: str = "1.0"
    timestamp: str = field(default_factory=utc_now_iso)

    def validate(self) -> bool:
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.event_type:
            raise ValueError("event_type is required")
        if not self.source_object_id:
            raise ValueError("source_object_id is required")
        if not self.source_object_type:
            raise ValueError("source_object_type is required")
        if not self.version:
            raise ValueError("version is required")
        return True

    def serialize(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    def to_dict(self) -> dict[str, Any]:
        return self.serialize()

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "CanonicalEvent":
        if not data:
            raise ValueError("Event data is required")

        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            source_object_id=data["source_object_id"],
            source_object_type=data["source_object_type"],
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
            target_object_id=data.get("target_object_id"),
            target_object_type=data.get("target_object_type"),
            version=data.get("version", "1.0"),
            timestamp=data.get("timestamp", utc_now_iso()),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalEvent":
        return cls.deserialize(data)

    @classmethod
    def from_object(
        cls,
        event_id: str,
        event_type: str,
        source_object: Any,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "CanonicalEvent":
        return cls(
            event_id=event_id,
            event_type=event_type,
            source_object_id=source_object.object_id,
            source_object_type=source_object.object_type,
            payload=payload or {},
            metadata=metadata or {},
        )
