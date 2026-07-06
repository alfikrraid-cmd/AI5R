import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from IDENTITY.identity_object import IdentityObject


def test_identity_object():

    identity = IdentityObject(
        organization_id="ORG-001",
        identity_name="AI5R Enterprise",
        vision="Build Enterprise Digital Organizations",
        mission="Deliver trustworthy AI employees",
        values=[
            "Integrity",
            "Long-term Thinking",
            "Evidence-based Decision",
        ],
        culture="Engineering First",
        personality="Professional",
        communication_style="Executive",
        brand="AI5R",
    )

    assert identity.object_type == "IDENTITY"
    assert identity.status == "ACTIVE"
    assert identity.identity_name == "AI5R Enterprise"
    assert identity.brand == "AI5R"
    assert identity.identity_id.startswith("ID-")
