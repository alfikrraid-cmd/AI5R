import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ROLE.role_engine import RoleEngine
from ROLE.role_object import RoleObject


def test_role_engine():

    engine = RoleEngine()

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

    result = engine.build(role)

    assert result["status"] == "READY"
    assert result["role"] == role
    assert result["profile"]["authority_level"] == 100
    assert result["profile"]["response_style"] == "EXECUTIVE"
