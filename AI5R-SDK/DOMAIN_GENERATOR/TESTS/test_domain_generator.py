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

    assert (domain_path / "SPECIFICATION" / "specification.py").exists()
    assert (domain_path / "FACTORY" / "factory.py").exists()
    assert (domain_path / "ARTIFACT" / "artifact.py").exists()
    assert (domain_path / "REGISTRY" / "registry.py").exists()
    assert (domain_path / "RUNTIME" / "runtime.py").exists()
    assert (domain_path / "TESTS" / "test_domain.py").exists()
    assert (domain_path / "domain_manifest.py").exists()
    assert (domain_path / "README.md").exists()


def test_generated_domain_test_file_is_valid(tmp_path):
    generator = AI5RDomainGenerator(tmp_path)
    generator.generate("sample domain")

    test_file = tmp_path / "SAMPLE_DOMAIN" / "TESTS" / "test_domain.py"

    assert "SampleDomainSpecification" in test_file.read_text()
    assert "SampleDomainFactory" in test_file.read_text()
    assert "SampleDomainArtifact" in test_file.read_text()
    assert "SampleDomainRegistry" in test_file.read_text()
    assert "SampleDomainRuntime" in test_file.read_text()


def test_domain_generator_rejects_empty_domain_name(tmp_path):
    generator = AI5RDomainGenerator(tmp_path)

    try:
        generator.generate("")
    except ValueError as error:
        assert str(error) == "domain_name is required"
    else:
        raise AssertionError("Expected ValueError")
