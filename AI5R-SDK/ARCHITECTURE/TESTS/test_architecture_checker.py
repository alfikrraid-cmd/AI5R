import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.EAS.architecture_checker import ArchitectureChecker


def test_checker():

    checker = ArchitectureChecker()

    result = checker.check(
        {
            "uses_enterprise_object": True,
            "uses_station": True,
            "uses_factory_orchestration": True,
            "produces_digital_thread": True,
            "preserves_cognitive_context": True,
        }
    )

    assert result["score"] == 100
    assert result["valid"]
