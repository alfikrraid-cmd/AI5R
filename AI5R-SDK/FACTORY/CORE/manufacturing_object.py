from dataclasses import dataclass, field
from typing import Any


@dataclass
class ManufacturingObject:
    object_type: str
    object_id: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.object_type,
            "object_id": self.object_id,
            "payload": self.payload,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }
