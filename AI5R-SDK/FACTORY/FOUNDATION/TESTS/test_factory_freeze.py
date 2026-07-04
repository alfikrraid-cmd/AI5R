from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.factory_freeze import FactoryFreeze


def test_factory_freeze_creates_freeze_record():
    freezer = FactoryFreeze()

    result = freezer.freeze(
        product="LTSA-BRAIN",
        version="1.0",
        result={
            "status": "FACTORY_COMPILED",
        },
    )

    assert result["status"] == "FROZEN"
    assert result["product"] == "LTSA-BRAIN"
    assert result["version"] == "1.0"
    assert result["result"]["status"] == "FACTORY_COMPILED"
    assert "frozen_at" in result
