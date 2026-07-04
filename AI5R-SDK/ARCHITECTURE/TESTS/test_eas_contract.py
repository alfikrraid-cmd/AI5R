import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.EAS.eas_contract import EnterpriseArchitectureSpecification


def test_eas_contract():

    eas = EnterpriseArchitectureSpecification()

    assert eas.version == "1.0"
    assert eas.status == "canonical"
    assert len(eas.rules()) == 5

    print("EAS Contract OK")


if __name__ == "__main__":
    test_eas_contract()
