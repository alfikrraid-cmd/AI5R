from typing import Any

from .exceptions import ManufacturingValidationError
from .manufacturing_clock import ManufacturingClock
from .manufacturing_event import ManufacturingEvent
from .manufacturing_id import ManufacturingID
from .manufacturing_object import ManufacturingObject
from .manufacturing_result import ManufacturingResult


class BaseManufacturingStation:
    station_code: str = ""
    station_name: str = ""
    object_type: str = ""
    event_type: str = ""
    required_input: str = ""

    def full_station_name(self) -> str:
        return f"{self.station_code} {self.station_name}".strip()

    def validate(self, payload: dict[str, Any]) -> None:
        if self.required_input and not payload.get(self.required_input):
            raise ManufacturingValidationError(
                f"{self.required_input.replace('_', ' ').title()} is required"
            )

    def manufacture(
        self,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ManufacturingResult:
        self.validate(payload)

        manufactured_at = ManufacturingClock.now()
        object_id = ManufacturingID.generate()

        manufactured_object = ManufacturingObject(
            object_type=self.object_type,
            object_id=object_id,
            payload=payload,
            metadata=metadata or {},
            created_at=manufactured_at,
        ).to_dict()

        event = ManufacturingEvent(
            event_type=self.event_type,
            station=self.full_station_name(),
            object_id=object_id,
            created_at=manufactured_at,
        ).to_dict()

        return ManufacturingResult(
            status="MANUFACTURED",
            station=self.full_station_name(),
            manufactured_object=manufactured_object,
            object_id=object_id,
            manufactured_at=manufactured_at,
            events=[event],
        )
