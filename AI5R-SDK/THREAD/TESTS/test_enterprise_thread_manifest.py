import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from THREAD.enterprise_thread_manifest import EnterpriseThreadManifest


def test_enterprise_thread_manifest():
    manifest = EnterpriseThreadManifest()
    data = manifest.to_dict()

    assert data["subsystem"] == "THREAD"
    assert data["foundation_version"] == "1.0"
    assert data["runtime"] == "EnterpriseThreadRuntime"
    assert data["registry"] == "EnterpriseThreadRegistry"

    assert "EnterpriseThread" in data["objects"]
    assert "MISSION" in data["canonical_stations"]
    assert "REALITY" in data["canonical_stations"]
    assert "KNOWLEDGE" in data["canonical_stations"]
    assert "CAPABILITY" in data["canonical_stations"]
    assert "INNOVATION" in data["canonical_stations"]

    assert data["status"] == "FROZEN_CANDIDATE"

    print("TF-004 Enterprise Thread Manifest OK")


if __name__ == "__main__":
    test_enterprise_thread_manifest()
