import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ROLE.role_object import RoleObject


def test_role_object():

    role = RoleObject(
        role_name="CEO",
        organization_level=1,
        authority_level=100,
        reasoning_depth=100,
        risk_weight=1.0,
        mission_weight=1.0,
        policy_weight=1.0,
        knowledge_scope="GLOBAL",
        execution_permission="FULL",
        response_style="EXECUTIVE",
    )

    assert role.object_type == "ROLE"
    assert role.role_name == "CEO"
    assert role.authority_level == 100
    assert role.status == "ACTIVE"
