import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.EAS.eas_validator import EASValidator


def test_validator_pass():

    validator = EASValidator()

    result = validator.validate(
        {
            "uses_enterprise_object": True,
            "uses_station": True,
            "uses_factory_orchestration": True,
            "produces_digital_thread": True,
            "preserves_cognitive_context": True,
        }
    )

    assert result["valid"]


def test_validator_fail():

    validator = EASValidator()

    result = validator.validate(
        {
            "uses_enterprise_object": True,
        }
    )

    assert not result["valid"]
    assert len(result["missing"]) == 4


if __name__ == "__main__":
    test_validator_pass()
    test_validator_fail()
