from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.CONTRACTS.capability_contract import CapabilityManifest


def test_capability_manifest():
    manifest = CapabilityManifest(
        capability_id="UMKM",
        capability_name="UMKM Capability",
    )

    assert manifest.capability_id == "UMKM"
    assert manifest.capability_name == "UMKM Capability"
    assert manifest.version == "1.0.0"


if __name__ == "__main__":
    test_capability_manifest()
