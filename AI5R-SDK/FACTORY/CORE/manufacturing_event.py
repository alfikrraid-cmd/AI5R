from dataclasses import dataclass
from typing import Any


@dataclass
class ManufacturingEvent:
    event_type: str
    station: str
    object_id: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "station": self.station,
            "object_id": self.object_id,
            "created_at": self.created_at,
        }
