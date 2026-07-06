import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DOMAIN_GENERATOR import AI5RDomainGenerator


def test_domain_generator_creates_complete_domain(tmp_path):
    generator = AI5RDomainGenerator(tmp_path)

    result = generator.generate("digital employee")

    domain_path = tmp_path / "DIGITAL_EMPLOYEE"

    assert result["status"] == "DOMAIN_GENERATED"
    assert result["domain_name"] == "DIGITAL_EMPLOYEE"
    assert domain_path.exists()

    assert (domain_path / "SPECIFICATION").exists()
    assert (domain_path / "FACTORY").exists()
    assert (domain_path / "ARTIFACT").exists()
    assert (domain_path / "REGISTRY").exists()
    assert (domain_path / "RUNTIME").exists()
    assert (domain_path / "TESTS").exists()
    assert (domain_path / "domain_manifest.py").exists()


def test_domain_generator_rejects_empty_domain_name(tmp_path):
    generator = AI5RDomainGenerator(tmp_path)

    try:
        generator.generate("")
    except ValueError as error:
        assert str(error) == "domain_name is required"
    else:
        raise AssertionError("Expected ValueError")
