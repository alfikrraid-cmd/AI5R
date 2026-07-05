from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.factory_integration_freeze import FactoryIntegrationFreeze


def test_factory_integration_freeze_is_complete():
    foundation_dir = Path(__file__).resolve().parents[1]

    result = FactoryIntegrationFreeze(foundation_dir).verify()

    assert result["status"] == "FROZEN"
    assert result["missing"] == []
