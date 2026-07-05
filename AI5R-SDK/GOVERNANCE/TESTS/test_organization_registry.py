import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from GOVERNANCE.organization_object import OrganizationObject
from GOVERNANCE.organization_registry import OrganizationRegistry


def test_register_organization_object():
    registry = OrganizationRegistry()

    corporation = OrganizationObject(
        object_id="corp-ai5r",
        name="AI5R Corporation",
        object_type="corporation",
    )

    registry.register(corporation)

    result = registry.get("corp-ai5r")

    assert result.name == "AI5R Corporation"
    assert result.object_type == "corporation"


def test_children_of_organization_object():
    registry = OrganizationRegistry()

    corporation = OrganizationObject(
        object_id="corp-ai5r",
        name="AI5R Corporation",
        object_type="corporation",
    )

    executive = OrganizationObject(
        object_id="exec-ai5r",
        name="Executive Office",
        object_type="division",
        parent_id="corp-ai5r",
    )

    registry.register(corporation)
    registry.register(executive)

    children = registry.children_of("corp-ai5r")

    assert len(children) == 1
    assert children[0].name == "Executive Office"
