from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import ArchitectureVerifier


def test_architecture_verifier():
    verifier = ArchitectureVerifier(ROOT)

    result = verifier.verify()

    assert result.success
    assert len(result.checked) > 5
    assert result.missing == []


def test_verification_result():
    verifier = ArchitectureVerifier(ROOT)

    result = verifier.verify()

    assert result.status == "PASS"
    assert result.success is True
