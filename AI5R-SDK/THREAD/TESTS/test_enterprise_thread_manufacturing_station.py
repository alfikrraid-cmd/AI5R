import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from THREAD.enterprise_thread_manufacturing_station import (
    EnterpriseThreadManufacturingStation,
)


def test_enterprise_thread_manufacturing_station():
    station = EnterpriseThreadManufacturingStation()

    result = station.run()

    assert result["station"] == "enterprise_thread"
    assert result["status"] == "SUCCESS"

    manifest = result["manifest"]

    assert manifest["subsystem"] == "THREAD"
    assert manifest["runtime"] == "EnterpriseThreadRuntime"
    assert manifest["registry"] == "EnterpriseThreadRegistry"

    print("TF-005 Enterprise Thread Manufacturing Station OK")


if __name__ == "__main__":
    test_enterprise_thread_manufacturing_station()
