import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.capability_object import CapabilityObject
from CAPABILITY.capability_runtime import CapabilityRuntime


def test_capability_runtime():
    runtime = CapabilityRuntime()

    capability = CapabilityObject(
        organization_id="ORG-001",
        capability_code="CAP-005",
        capability_name="Pump Inspection",
        description="Runtime managed pump inspection capability",
        supported_domains=["maintenance"],
        required_knowledge_ids=["KN-001"],
        metadata={"owner": "AI5R"},
    )

    registration = runtime.register(capability)

    assert registration["status"] == "REGISTERED"
    assert registration["validation"]["valid"] is True

    execution = runtime.execute(
        capability_id=capability.capability_id,
        input_data={"asset_id": "PUMP-001"},
    )

    assert execution["status"] == "EXECUTED"
    assert execution["capability_code"] == "CAP-005"
    assert execution["input_data"]["asset_id"] == "PUMP-001"

    assert runtime.get(capability.capability_id) == capability
    assert runtime.list_by_domain("maintenance") == [capability]

    print("CP-005 Capability Runtime OK")


if __name__ == "__main__":
    test_capability_runtime()
