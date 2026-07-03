import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ENTERPRISE.enterprise_object import EnterpriseObject


def test_enterprise_object():
    obj = EnterpriseObject(
        code="ORG-AI5R",
        name="AI5R Corporation",
        type="organization",
        owner="CEO",
    )

    obj.add_tag("enterprise")
    obj.set_metadata("generation", "Gen-2")
    obj.update_status("active")

    data = obj.to_dict()

    assert data["code"] == "ORG-AI5R"
    assert data["name"] == "AI5R Corporation"
    assert data["type"] == "organization"
    assert data["owner"] == "CEO"
    assert data["status"] == "active"
    assert "enterprise" in data["tags"]
    assert data["metadata"]["generation"] == "Gen-2"
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    print("EL-002 Enterprise Object Contract OK")


if __name__ == "__main__":
    test_enterprise_object()
