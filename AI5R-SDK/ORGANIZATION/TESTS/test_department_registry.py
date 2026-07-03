import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ORGANIZATION.department_object import DepartmentObject
from ORGANIZATION.department_registry import DepartmentRegistry


def test_department_registry():
    registry = DepartmentRegistry()
    org_id = "ORG-001"

    executive = DepartmentObject(
        organization_id=org_id,
        department_code="EXEC",
        department_name="Executive Office",
    )
    registry.register(executive)

    engineering = DepartmentObject(
        organization_id=org_id,
        department_code="ENG",
        department_name="Engineering Department",
        parent_department_id=executive.department_id,
        policies={"cost_first": True, "llm_usage": "restricted"},
    )
    registry.register(engineering)

    hierarchy = registry.hierarchy(org_id)

    assert len(registry.list_by_organization(org_id)) == 2
    assert hierarchy["departments"][0]["department"]["department_code"] == "EXEC"
    assert hierarchy["departments"][0]["children"][0]["department"]["department_code"] == "ENG"

    print("OR-002 Department Registry OK")


if __name__ == "__main__":
    test_department_registry()
