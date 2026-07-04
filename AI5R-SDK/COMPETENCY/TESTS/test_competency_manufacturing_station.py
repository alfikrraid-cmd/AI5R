import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from COMPETENCY.competency_manufacturing_station import (
    CompetencyManufacturingStation,
)


def test_competency_manufacturing_station():
    station = CompetencyManufacturingStation()

    result = station.run()

    assert result["station"] == "competency"
    assert result["status"] == "SUCCESS"
    assert station.depends_on == ["capability"]

    manifest = result["manifest"]

    assert manifest["subsystem"] == "COMPETENCY"
    assert manifest["runtime"] == "CompetencyRuntime"
    assert manifest["registry"] == "CompetencyRegistry"
    assert "CAPABILITY" in manifest["depends_on"]

    print("CM-007 Competency Manufacturing Station OK")


if __name__ == "__main__":
    test_competency_manufacturing_station()
