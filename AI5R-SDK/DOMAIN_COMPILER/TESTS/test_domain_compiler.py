import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DOMAIN_COMPILER import AI5RDomainCompiler
from DOMAIN_GENERATOR import AI5RDomainGenerator


def test_domain_compiler_compiles_generated_domain(tmp_path):
    generator = AI5RDomainGenerator(tmp_path)
    generator.generate("digital employee")

    compiler = AI5RDomainCompiler(tmp_path)

    result = compiler.compile("digital employee")

    assert result["status"] == "COMPILED"
    assert result["domain"] == "DIGITAL_EMPLOYEE"
    assert result["version"] == "1.0"
    assert result["manifest_exists"] is True
    assert result["readme_exists"] is True
    assert "SPECIFICATION" in result["layers"]
    assert "FACTORY" in result["layers"]
    assert "ARTIFACT" in result["layers"]
    assert "REGISTRY" in result["layers"]
    assert "RUNTIME" in result["layers"]
    assert "compiled_at" in result


def test_domain_compiler_rejects_invalid_domain(tmp_path):
    compiler = AI5RDomainCompiler(tmp_path)

    result = compiler.compile("unknown domain")

    assert result["status"] == "FAILED"
    assert result["reason"] == "DOMAIN_VALIDATION_FAILED"
    assert result["validation"]["status"] == "INVALID"
