from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RealityManufacturingInput:
    source: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RealityManufacturingResult:
    status: str
    station: str
    source: str
    manufactured_at: str
    reality_object: dict[str, Any]
    events: list[dict[str, Any]]


class RealityManufacturingStation:
    station_name = "MS-001 Reality Manufacturing Station"

    def manufacture(
        self,
        manufacturing_input: RealityManufacturingInput,
        context: dict[str, Any] | None = None,
    ) -> RealityManufacturingResult:
        if not manufacturing_input.source:
            raise ValueError("Reality source is required")

        manufactured_at = datetime.now(timezone.utc).isoformat()

        reality_object = {
            "type": "REALITY_OBJECT",
            "source": manufacturing_input.source,
            "payload": manufacturing_input.payload,
            "metadata": manufacturing_input.metadata,
            "context": context or {},
            "manufactured_at": manufactured_at,
        }

        events = [
            {
                "event_type": "REALITY_MANUFACTURED",
                "station": self.station_name,
                "source": manufacturing_input.source,
                "created_at": manufactured_at,
            }
        ]

        return RealityManufacturingResult(
            status="MANUFACTURED",
            station=self.station_name,
            source=manufacturing_input.source,
            manufactured_at=manufactured_at,
            reality_object=reality_object,
            events=events,
        )
