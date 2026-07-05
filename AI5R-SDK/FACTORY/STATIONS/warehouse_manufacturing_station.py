from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class WarehouseManufacturingInput:
    reality_object: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WarehouseManufacturingResult:
    status: str
    station: str
    warehouse_object: dict[str, Any]
    warehouse_id: str
    warehouse_timestamp: str
    events: list[dict[str, Any]]


class WarehouseManufacturingStation:
    station_name = "MS-002 Warehouse Manufacturing Station"

    def manufacture(
        self,
        manufacturing_input: WarehouseManufacturingInput,
    ) -> WarehouseManufacturingResult:
        if not manufacturing_input.reality_object:
            raise ValueError("Reality object is required")

        warehouse_timestamp = datetime.now(timezone.utc).isoformat()
        warehouse_id = str(uuid4())

        warehouse_object = {
            "type": "WAREHOUSE_OBJECT",
            "warehouse_id": warehouse_id,
            "reality_object": manufacturing_input.reality_object,
            "metadata": manufacturing_input.metadata,
            "warehouse_timestamp": warehouse_timestamp,
        }

        events = [
            {
                "event_type": "WAREHOUSE_OBJECT_STORED",
                "station": self.station_name,
                "warehouse_id": warehouse_id,
                "created_at": warehouse_timestamp,
            }
        ]

        return WarehouseManufacturingResult(
            status="MANUFACTURED",
            station=self.station_name,
            warehouse_object=warehouse_object,
            warehouse_id=warehouse_id,
            warehouse_timestamp=warehouse_timestamp,
            events=events,
        )
