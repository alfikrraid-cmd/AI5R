import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from POSITION.position_object import PositionObject


def test_position_object():

    position = PositionObject(
        organization_id="ORG-001",
        position_code="CEO",
        position_name="Chief Executive Officer",
        department="Executive",
        authority_level=100,
        approval_limit=999999999,
    )

    assert position.object_type == "POSITION"
    assert position.status == "ACTIVE"
    assert position.position_code == "CEO"
    assert position.department == "Executive"
    assert position.authority_level == 100
    assert position.position_id.startswith("POS-")
