import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.EAS.compliance_report import ComplianceReport


def test_report():

    report = ComplianceReport().generate(
        "WarehouseAdapterStation",
        {
            "valid": True,
            "score": 100,
            "missing": [],
        },
    )

    assert report["status"] == "CERTIFIED"
    assert report["score"] == 100
