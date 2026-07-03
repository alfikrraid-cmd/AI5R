import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ENTERPRISE.enterprise_object import EnterpriseObject
from ENTERPRISE.enterprise_registry import EnterpriseRegistry


def test_enterprise_registry():
    registry = EnterpriseRegistry("department")

    req_dept = EnterpriseObject(
        code="DEPT-REQ",
        name="Requirement Department",
        type="department",
        owner="CTO",
        tags=["factory", "requirement"],
    )

    registry.register(req_dept)

    assert registry.get("DEPT-REQ").name == "Requirement Department"
    assert len(registry.list()) == 1

    registry.update_status("DEPT-REQ", "active")
    assert registry.get("DEPT-REQ").status == "active"

    result = registry.find_by_tag("requirement")
    assert len(result) == 1
    assert result[0].code == "DEPT-REQ"

    data = registry.to_dict()
    assert data["object_type"] == "department"
    assert data["count"] == 1

    print("EL-003 Enterprise Registry Engine OK")


if __name__ == "__main__":
    test_enterprise_registry()
