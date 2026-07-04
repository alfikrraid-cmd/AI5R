import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.capability_object import CapabilityObject
from CAPABILITY.capability_validation_engine import CapabilityValidationEngine


def test_capability_validation_engine():
    capability = CapabilityObject(
        organization_id="ORG-001",
        capability_code="CAP-004",
        capability_name="Pump Inspection",
        description="Validate pump inspection capability",
        supported_domains=["maintenance"],
        required_knowledge_ids=["KN-001"],
    )

    validator = CapabilityValidationEngine()
    result = validator.validate(capability)

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["capability_code"] == "CAP-004"

    print("CP-004 Capability Validation Engine OK")


if __name__ == "__main__":
    test_capability_validation_engine()
