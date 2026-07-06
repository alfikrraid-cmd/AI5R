import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DOMAIN_GENERATOR import AI5RDomainGenerator
from DOMAIN_VALIDATOR import AI5RDomainValidator


def test_domain_validator_accepts_generated_domain(tmp_path):
    generator = AI5RDomainGenerator(tmp_path)
    generator.generate("digital employee")

    validator = AI5RDomainValidator(tmp_path)
    result = validator.validate("digital employee")

    assert result["status"] == "VALID"
    assert result["domain"] == "DIGITAL_EMPLOYEE"
    assert result["score"] == 100
    assert result["missing"] == []
    assert result["warnings"] == []


def test_domain_validator_detects_missing_domain(tmp_path):
    validator = AI5RDomainValidator(tmp_path)

    result = validator.validate("missing domain")

    assert result["status"] == "INVALID"
    assert result["domain"] == "MISSING_DOMAIN"
    assert result["score"] == 0
    assert "DOMAIN" in result["missing"]


def test_domain_validator_detects_missing_layer(tmp_path):
    domain_path = tmp_path / "BROKEN_DOMAIN"
    domain_path.mkdir(parents=True)
    (domain_path / "SPECIFICATION").mkdir()
    (domain_path / "SPECIFICATION" / "__init__.py").touch()

    validator = AI5RDomainValidator(tmp_path)
    result = validator.validate("broken domain")

    assert result["status"] == "INVALID"
    assert "FACTORY" in result["missing"]
    assert "ARTIFACT" in result["missing"]
    assert "REGISTRY" in result["missing"]
    assert "RUNTIME" in result["missing"]
    assert "TESTS" in result["missing"]


def test_domain_validator_rejects_empty_domain_name(tmp_path):
    validator = AI5RDomainValidator(tmp_path)

    try:
        validator.validate("")
    except ValueError as error:
        assert str(error) == "domain_name is required"
    else:
        raise AssertionError("Expected ValueError")
