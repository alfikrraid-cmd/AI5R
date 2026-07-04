import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.capability_engine import CapabilityEngine
from CAPABILITY.capability_object import CapabilityObject


def test_capability_engine():
    capability = CapabilityObject(
        organization_id="ORG-001",
        capability_code="CAP-002",
        capability_name="Pump Inspection",
        description="Execute pump inspection capability",
        supported_domains=["maintenance"],
        required_knowledge_ids=["KN-001"],
        metadata={"priority": "high"},
    )

    engine = CapabilityEngine()

    result = engine.execute(
        capability,
        input_data={"asset_id": "PUMP-001"},
    )

    assert result["status"] == "EXECUTED"
    assert result["capability_code"] == "CAP-002"
    assert result["input_data"]["asset_id"] == "PUMP-001"

    print("CP-002 Capability Engine OK")


if __name__ == "__main__":
    test_capability_engine()
