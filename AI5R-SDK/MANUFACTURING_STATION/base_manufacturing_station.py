from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


@dataclass
class ManufacturingContext:
    product: str
    payload: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    def add_event(self, station_code: str, station_name: str, status: str):
        self.history.append({
            "station_code": station_code,
            "station_name": station_name,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
        })


class BaseManufacturingStation:
    station_code = "BASE"
    station_name = "Base Manufacturing Station"

    def execute(self, context: ManufacturingContext):
        if context is None:
            raise ValueError("context is required")

        context.add_event(
            self.station_code,
            self.station_name,
            "COMPLETED",
        )

        return context
