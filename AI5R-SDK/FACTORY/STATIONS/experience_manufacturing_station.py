from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class ExperienceManufacturingInput:
    warehouse_object: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperienceManufacturingResult:
    status: str
    station: str
    experience_object: dict[str, Any]
    experience_id: str
    experience_timestamp: str
    events: list[dict[str, Any]]


class ExperienceManufacturingStation:
    station_name = "MS-003 Experience Manufacturing Station"

    def manufacture(
        self,
        manufacturing_input: ExperienceManufacturingInput,
    ) -> ExperienceManufacturingResult:

        if not manufacturing_input.warehouse_object:
            raise ValueError("Warehouse object is required")

        experience_timestamp = datetime.now(timezone.utc).isoformat()
        experience_id = str(uuid4())

        experience_object = {
            "type": "EXPERIENCE_OBJECT",
            "experience_id": experience_id,
            "warehouse_object": manufacturing_input.warehouse_object,
            "metadata": manufacturing_input.metadata,
            "experience_timestamp": experience_timestamp,
        }

        events = [
            {
                "event_type": "EXPERIENCE_MANUFACTURED",
                "station": self.station_name,
                "experience_id": experience_id,
                "created_at": experience_timestamp,
            }
        ]

        return ExperienceManufacturingResult(
            status="MANUFACTURED",
            station=self.station_name,
            experience_object=experience_object,
            experience_id=experience_id,
            experience_timestamp=experience_timestamp,
            events=events,
        )
