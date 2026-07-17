from __future__ import annotations

import sys
from pathlib import Path

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from MANUFACTURING.FACTORY import DigitalFactory

_digital_factory: DigitalFactory | None = None


def get_digital_factory() -> DigitalFactory:
    global _digital_factory

    if _digital_factory is None:
        _digital_factory = DigitalFactory(
            factory_id="DF-001",
            factory_name="AI5R Digital Factory",
        )

    return _digital_factory
