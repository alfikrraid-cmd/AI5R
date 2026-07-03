import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from LTSA.pump_finding_extractor import PumpFindingExtractor


def test_pump_finding_extractor():
    report = """
    Pump inspection shows high vibration near bearing housing.
    Mechanical seal leakage observed.
    Lubrication condition needs review.
    """

    extractor = PumpFindingExtractor()
    findings = extractor.extract(report)

    assert findings["vibration"]
    assert findings["bearing"]
    assert findings["seal"]
    assert findings["lubrication"]


if __name__ == "__main__":
    test_pump_finding_extractor()
    print("LTSA-003 Pump Finding Extractor OK")
