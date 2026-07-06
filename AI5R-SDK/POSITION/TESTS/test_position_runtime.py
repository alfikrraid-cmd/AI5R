import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from POSITION.position_object import PositionObject
from POSITION.position_runtime import PositionRuntime


def test_position_runtime():

    runtime = PositionRuntime()

    ceo = PositionObject(
        organization_id="ORG-001",
        position_code="CEO",
        position_name="Chief Executive Officer",
        department="Executive",
        authority_level=100,
        approval_limit=999999999,
    )

    registration = runtime.register(ceo)

    assert registration["status"] == "REGISTERED"

    stored = runtime.get(ceo.position_id)

    assert stored["status"] == "READY"
    assert stored["position"] == ceo

    assert runtime.list_all() == [stored]
    assert runtime.list_by_department("Executive") == [stored]
    assert runtime.list_by_authority(90) == [stored]
