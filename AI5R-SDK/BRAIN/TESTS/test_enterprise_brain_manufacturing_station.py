import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.enterprise_brain_manufacturing_station import (
    EnterpriseBrainManufacturingStation,
)


def test_manufacturing_station():

    station = EnterpriseBrainManufacturingStation()

    product = station.manufacture()

    assert product["status"] == "manufactured"

    assert product["product_type"] == "enterprise_brain"

    assert product["manifest"]["brain_name"] == "Enterprise Brain"

    assert product["manifest"]["supported_input"] == "reality"

    assert product["manifest"]["supported_output"] == "learning"

    assert product["runtime"] is not None


def test_station_metadata():

    station = EnterpriseBrainManufacturingStation()

    assert station.station_name == "Enterprise Brain Manufacturing Station"

    assert station.station_version == "1.0"
