import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from POSITION.position_object import PositionObject
from POSITION.position_hierarchy import PositionHierarchy


def test_position_hierarchy():

    hierarchy = PositionHierarchy()

    ceo = PositionObject(
        organization_id="ORG-001",
        position_code="CEO",
        position_name="Chief Executive Officer",
        department="Executive",
        authority_level=100,
    )

    cmo = PositionObject(
        organization_id="ORG-001",
        position_code="CMO",
        position_name="Chief Marketing Officer",
        department="Marketing",
        reports_to=ceo.position_id,
        authority_level=80,
    )

    staff = PositionObject(
        organization_id="ORG-001",
        position_code="MKT-STAFF",
        position_name="Marketing Staff",
        department="Marketing",
        reports_to=cmo.position_id,
        authority_level=20,
    )

    hierarchy.add(ceo)
    hierarchy.add(cmo)
    hierarchy.add(staff)

    assert hierarchy.get_manager(cmo) == ceo
    assert hierarchy.get_manager(staff) == cmo
    assert hierarchy.get_direct_reports(ceo) == [cmo]
    assert hierarchy.get_direct_reports(cmo) == [staff]
    assert hierarchy.get_chain_of_command(staff) == [cmo, ceo]
