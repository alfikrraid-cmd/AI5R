import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MEMORY.memory_manufacturing_station import (
    EnterpriseMemoryManufacturingStation,
)


def test_memory_manufacturing_station():

    station = EnterpriseMemoryManufacturingStation()

    product = station.manufacture()

    assert product["status"] == "manufactured"

    assert product["product_type"] == "enterprise_memory"

    assert product["manifest"]["memory_name"] == "Enterprise Memory"

    assert product["manifest"]["supported_input"] == "learning"

    assert product["manifest"]["supported_output"] == "memory"

    assert product["runtime"] is not None


def test_station_metadata():

    station = EnterpriseMemoryManufacturingStation()

    assert station.station_name == "Enterprise Memory Manufacturing Station"

    assert station.station_version == "1.0"
