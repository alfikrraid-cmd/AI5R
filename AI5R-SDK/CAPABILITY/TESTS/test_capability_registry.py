from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.CONTRACTS.capability_contract import CapabilityManifest
from CAPABILITY.capability_registry import CapabilityRegistry


def test_capability_registry_registers_manifest():
    registry = CapabilityRegistry()

    manifest = CapabilityManifest(
        capability_id="UMKM",
        capability_name="UMKM Capability",
    )

    registry.register(manifest)

    assert registry.exists("UMKM") is True
    assert registry.get("UMKM").capability_name == "UMKM Capability"
    assert len(registry.list_all()) == 1


def test_capability_registry_rejects_empty_id():
    registry = CapabilityRegistry()

    manifest = CapabilityManifest(
        capability_id="",
        capability_name="Invalid Capability",
    )

    try:
        registry.register(manifest)
        assert False
    except ValueError as error:
        assert str(error) == "capability_id is required"
