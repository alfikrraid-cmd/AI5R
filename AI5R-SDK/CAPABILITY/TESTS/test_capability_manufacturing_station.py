import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.capability_manufacturing_station import (
    CapabilityManufacturingStation,
)


def test_capability_manufacturing_station():
    station = CapabilityManufacturingStation()

    result = station.run()

    assert result["station"] == "capability"
    assert result["status"] == "SUCCESS"

    manifest = result["manifest"]

    assert manifest["subsystem"] == "CAPABILITY"
    assert manifest["runtime"] == "CapabilityRuntime"
    assert manifest["registry"] == "CapabilityRegistry"

    print("CP-007 Capability Manufacturing Station OK")


if __name__ == "__main__":
    test_capability_manufacturing_station()
