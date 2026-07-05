from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.warehouse_manufacturing_station import (
    WarehouseManufacturingInput,
    WarehouseManufacturingStation,
)


def test_station_manufactures_warehouse_object():
    station = WarehouseManufacturingStation()

    result = station.manufacture(
        WarehouseManufacturingInput(
            reality_object={
                "type": "REALITY_OBJECT",
                "source": "manual_input",
                "payload": {"observation": "customer needs product recommendation"},
            },
            metadata={"product": "LTSA-BRAIN"},
        )
    )

    assert result.status == "MANUFACTURED"
    assert result.station == "MS-002 Warehouse Manufacturing Station"
    assert result.warehouse_object["type"] == "WAREHOUSE_OBJECT"
    assert result.warehouse_id
    assert result.warehouse_object["warehouse_id"] == result.warehouse_id
    assert result.warehouse_object["metadata"]["product"] == "LTSA-BRAIN"
    assert result.events[0]["event_type"] == "WAREHOUSE_OBJECT_STORED"


def test_station_requires_reality_object():
    station = WarehouseManufacturingStation()

    try:
        station.manufacture(
            WarehouseManufacturingInput(
                reality_object={},
            )
        )
    except ValueError as exc:
        assert str(exc) == "Reality object is required"
    else:
        raise AssertionError("Expected ValueError")


def test_timestamp_timezone_aware():
    result = WarehouseManufacturingStation().manufacture(
        WarehouseManufacturingInput(
            reality_object={
                "type": "REALITY_OBJECT",
                "source": "sensor",
                "payload": {"signal": "ok"},
            }
        )
    )

    parsed = datetime.fromisoformat(result.warehouse_timestamp)

    assert parsed.tzinfo is not None
