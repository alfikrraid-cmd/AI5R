import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from POSITION.position_object import PositionObject
from POSITION.board_engine import BoardEngine


def test_board_engine():

    engine = BoardEngine()

    ceo = PositionObject(
        organization_id="ORG-001",
        position_code="CEO",
        position_name="Chief Executive Officer",
        department="Executive",
        authority_level=100,
    )

    cfo = PositionObject(
        organization_id="ORG-001",
        position_code="CFO",
        position_name="Chief Finance Officer",
        department="Finance",
        authority_level=85,
    )

    cmo = PositionObject(
        organization_id="ORG-001",
        position_code="CMO",
        position_name="Chief Marketing Officer",
        department="Marketing",
        authority_level=80,
    )

    result = engine.convene(
        topic="Evaluate new business expansion",
        positions=[cfo, cmo, ceo],
        agenda={
            "objective": "Decide whether expansion is viable",
        },
    )

    assert result["status"] == "CONVENED"
    assert result["topic"] == "Evaluate new business expansion"
    assert result["chair"]["position_code"] == "CEO"
    assert len(result["members"]) == 3
    assert result["agenda"]["objective"] == "Decide whether expansion is viable"


def test_board_engine_rejects_empty_positions():

    engine = BoardEngine()

    result = engine.convene(
        topic="Empty board",
        positions=[],
    )

    assert result["status"] == "REJECTED"
