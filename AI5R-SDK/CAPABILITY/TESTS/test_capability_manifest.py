import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.capability_manifest import CapabilityManifest


def test_capability_manifest():
    manifest = CapabilityManifest()
    data = manifest.to_dict()

    assert data["subsystem"] == "CAPABILITY"
    assert data["foundation_version"] == "1.0"
    assert data["runtime"] == "CapabilityRuntime"
    assert data["registry"] == "CapabilityRegistry"

    assert "CapabilityEngine" in data["engines"]
    assert "CapabilityValidationEngine" in data["engines"]
    assert "CapabilityObject" in data["objects"]

    assert data["status"] == "FROZEN_CANDIDATE"

    print("CP-006 Capability Manifest OK")


if __name__ == "__main__":
    test_capability_manifest()
