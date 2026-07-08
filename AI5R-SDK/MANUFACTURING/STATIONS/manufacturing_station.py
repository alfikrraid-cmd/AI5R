from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


@dataclass(frozen=True)
class ManufacturingStation:
    station_id: str
    station_name: str
    station_type: str
    capability_required: str
    status: StationStatus = StationStatus.ACTIVE
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)
    canonical_base: str = "ManufacturingObject"

    def validate(self) -> bool:
        return bool(
            self.station_id
            and self.station_name
            and self.station_type
            and self.capability_required
            and self.canonical_base == "ManufacturingObject"
        )

    def is_available(self) -> bool:
        return self.status == StationStatus.ACTIVE
