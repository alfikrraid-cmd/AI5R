import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from POSITION.position_object import PositionObject
from POSITION.position_engine import PositionEngine


def test_position_engine():

    engine = PositionEngine()

    position = PositionObject(
        organization_id="ORG-001",
        position_code="CEO",
        position_name="Chief Executive Officer",
        department="Executive",
        authority_level=100,
        approval_limit=999999999,
    )

    result = engine.build(position)

    assert result["status"] == "READY"
    assert result["position"] == position
    assert result["profile"]["position_code"] == "CEO"
    assert result["profile"]["authority_level"] == 100
