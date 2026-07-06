import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from POSITION.position_object import PositionObject
from POSITION.delegation_engine import DelegationEngine


def test_delegation_engine():

    engine = DelegationEngine()

    ceo = PositionObject(
        organization_id="ORG-001",
        position_code="CEO",
        position_name="Chief Executive Officer",
        department="Executive",
        authority_level=100,
    )

    staff = PositionObject(
        organization_id="ORG-001",
        position_code="MKT-STAFF",
        position_name="Marketing Staff",
        department="Marketing",
        reports_to=ceo.position_id,
        authority_level=20,
    )

    result = engine.delegate(
        source_position=ceo,
        target_position=staff,
        task={
            "task_id": "TASK-001",
            "description": "Prepare campaign options",
        },
    )

    assert result["status"] == "DELEGATED"
    assert result["source_position_id"] == ceo.position_id
    assert result["target_position_id"] == staff.position_id
    assert result["task"]["task_id"] == "TASK-001"


def test_delegation_rejects_higher_authority():

    engine = DelegationEngine()

    staff = PositionObject(
        organization_id="ORG-001",
        position_code="MKT-STAFF",
        position_name="Marketing Staff",
        department="Marketing",
        authority_level=20,
    )

    ceo = PositionObject(
        organization_id="ORG-001",
        position_code="CEO",
        position_name="Chief Executive Officer",
        department="Executive",
        authority_level=100,
    )

    result = engine.delegate(
        source_position=staff,
        target_position=ceo,
        task={
            "task_id": "TASK-002",
            "description": "Approve strategy",
        },
    )

    assert result["status"] == "REJECTED"
