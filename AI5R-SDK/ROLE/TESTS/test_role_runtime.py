import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ROLE.role_object import RoleObject
from ROLE.role_runtime import RoleRuntime


def test_role_runtime():

    runtime = RoleRuntime()

    ceo = RoleObject(
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

    registration = runtime.register(ceo)

    assert registration["status"] == "REGISTERED"

    stored = runtime.get(ceo.role_id)

    assert stored["status"] == "READY"
    assert stored["role"].role_name == "CEO"

    assert len(runtime.list_all()) == 1
