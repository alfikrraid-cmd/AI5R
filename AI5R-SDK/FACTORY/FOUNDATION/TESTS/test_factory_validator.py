from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.factory_validator import FactoryValidator


def test_factory_validator_accepts_valid_definition():
    validator = FactoryValidator()

    result = validator.validate({
        "product": "LTSA-BRAIN",
        "version": "1.0",
        "factory": "AI5R",
    })

    assert result["status"] == "VALID"
    assert result["errors"] == []


def test_factory_validator_rejects_missing_fields():
    validator = FactoryValidator()

    result = validator.validate({
        "product": "LTSA-BRAIN",
    })

    assert result["status"] == "INVALID"
    assert "Missing required field: version" in result["errors"]
    assert "Missing required field: factory" in result["errors"]
