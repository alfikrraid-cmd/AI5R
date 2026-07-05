from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class CanonicalObject:
    object_id: str
    object_type: str
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def validate(self) -> bool:
        if not self.object_id:
            raise ValueError("object_id is required")
        if not self.object_type:
            raise ValueError("object_type is required")
        if not self.version:
            raise ValueError("version is required")
        return True

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def serialize(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    def to_dict(self) -> dict[str, Any]:
        return self.serialize()

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "CanonicalObject":
        if not data:
            raise ValueError("Object data is required")

        return cls(
            object_id=data["object_id"],
            object_type=data["object_type"],
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalObject":
        return cls.deserialize(data)

    def to_event(self, event_type: str) -> dict[str, Any]:
        self.validate()

        if not event_type:
            raise ValueError("event_type is required")

        return {
            "event_type": event_type,
            "object_id": self.object_id,
            "object_type": self.object_type,
            "version": self.version,
            "metadata": self.metadata,
            "timestamp": utc_now_iso(),
        }
