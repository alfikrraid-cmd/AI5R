import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.EAS.certification import ArchitectureCertification


def test_certification():

    cert = ArchitectureCertification()

    assert cert.certify({"status": "CERTIFIED"})
    assert not cert.certify({"status": "REJECTED"})
