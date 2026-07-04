import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.capability_object import CapabilityObject
from CAPABILITY.capability_registry import CapabilityRegistry


def test_capability_registry():
    registry = CapabilityRegistry()

    capability = CapabilityObject(
        organization_id="ORG-001",
        capability_code="CAP-003",
        capability_name="Pump Inspection",
        description="Register pump inspection capability",
        supported_domains=["maintenance", "asset"],
        required_knowledge_ids=["KN-001"],
    )

    registered = registry.register(capability)

    assert registered == capability
    assert registry.exists(capability.capability_id) is True
    assert registry.get(capability.capability_id) == capability
    assert len(registry.list_all()) == 1
    assert registry.list_by_organization("ORG-001") == [capability]
    assert registry.list_by_domain("maintenance") == [capability]
    assert registry.list_by_status("ACTIVE") == [capability]

    print("CP-003 Capability Registry OK")


if __name__ == "__main__":
    test_capability_registry()
