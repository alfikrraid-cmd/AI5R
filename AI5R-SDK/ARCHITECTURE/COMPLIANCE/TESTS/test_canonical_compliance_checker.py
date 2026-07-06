import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from DOMAIN_GENERATOR import AI5RDomainGenerator
from ARCHITECTURE.COMPLIANCE import CanonicalComplianceChecker


def test_compliant_domain(tmp_path):
    AI5RDomainGenerator(tmp_path).generate("digital employee")

    checker = CanonicalComplianceChecker(tmp_path)

    result = checker.check("digital employee")

    assert result["status"] == "COMPLIANT"
    assert result["score"] == 100
    assert result["missing"] == []


def test_non_compliant_domain(tmp_path):
    broken = tmp_path / "BROKEN_DOMAIN"
    broken.mkdir()
    (broken / "SPECIFICATION").mkdir()

    checker = CanonicalComplianceChecker(tmp_path)

    result = checker.check("broken domain")

    assert result["status"] == "NON_COMPLIANT"
    assert "FACTORY" in result["missing"]
    assert result["score"] < 100


def test_unknown_domain():
    checker = CanonicalComplianceChecker(Path("/tmp"))

    result = checker.check("does not exist")

    assert result["status"] == "NON_COMPLIANT"
    assert result["score"] == 0
