import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.capability_object import CapabilityObject


def test_capability_object():
    capability = CapabilityObject(
        organization_id="ORG-001",
        capability_code="CAP-001",
        capability_name="Pump Inspection",
        description="Perform enterprise pump inspection",
        supported_domains=["maintenance"],
        required_knowledge_ids=["KN-001"],
    )

    assert capability.organization_id == "ORG-001"
    assert capability.capability_code == "CAP-001"
    assert capability.capability_name == "Pump Inspection"
    assert capability.object_type == "CAPABILITY"

    print("CP-001 Capability Object OK")


if __name__ == "__main__":
    test_capability_object()
