import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from COMPETENCY.competency_manifest import CompetencyManifest


def test_competency_manifest():
    manifest = CompetencyManifest()
    data = manifest.to_dict()

    assert data["subsystem"] == "COMPETENCY"
    assert data["foundation_version"] == "1.0"
    assert data["runtime"] == "CompetencyRuntime"
    assert data["registry"] == "CompetencyRegistry"

    assert "CompetencyMeasurementEngine" in data["engines"]
    assert "CompetencyValidationEngine" in data["engines"]
    assert "CompetencyObject" in data["objects"]
    assert "CAPABILITY" in data["depends_on"]

    assert data["status"] == "FROZEN_CANDIDATE"

    print("CM-006 Competency Manifest OK")


if __name__ == "__main__":
    test_competency_manifest()
