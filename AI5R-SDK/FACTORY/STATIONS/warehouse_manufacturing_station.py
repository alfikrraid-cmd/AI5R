from dataclasses import dataclass, field
from typing import Any

from FACTORY.CORE import BaseManufacturingStation


@dataclass
class WarehouseManufacturingInput:
    reality_object: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class WarehouseManufacturingStation(BaseManufacturingStation):
    station_code = "MS-002"
    station_name = "Warehouse Manufacturing Station"
    object_type = "WAREHOUSE_OBJECT"
    event_type = "WAREHOUSE_OBJECT_STORED"
    required_input = "reality_object"

    def manufacture(
        self,
        manufacturing_input: WarehouseManufacturingInput,
    ):
        if not manufacturing_input.reality_object:
            raise ValueError("Reality object is required")

        result = super().manufacture(
            payload={
                "reality_object": manufacturing_input.reality_object,
            },
            metadata=manufacturing_input.metadata,
        )

        result.warehouse_id = result.object_id
        result.warehouse_timestamp = result.manufactured_at
        result.warehouse_object = {
            "type": "WAREHOUSE_OBJECT",
            "warehouse_id": result.object_id,
            "reality_object": manufacturing_input.reality_object,
            "metadata": manufacturing_input.metadata,
            "warehouse_timestamp": result.manufactured_at,
        }

        result.events[0]["warehouse_id"] = result.object_id

        return result


WarehouseManufacturingResult = object
