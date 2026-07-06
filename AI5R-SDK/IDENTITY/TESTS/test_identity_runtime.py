import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from IDENTITY.identity_object import IdentityObject
from IDENTITY.identity_runtime import IdentityRuntime


def test_identity_runtime():

    runtime = IdentityRuntime()

    identity = IdentityObject(
        organization_id="ORG-001",
        identity_name="AI5R Enterprise",
        vision="Build Enterprise Digital Organizations",
        mission="Deliver trustworthy AI employees",
        values=["Integrity", "Evidence-based Decision"],
        culture="Engineering First",
        personality="Professional",
        communication_style="Executive",
        brand="AI5R",
    )

    registration = runtime.register(identity)

    assert registration["status"] == "REGISTERED"

    stored = runtime.get(identity.identity_id)

    assert stored["status"] == "READY"
    assert stored["identity"] == identity

    assert runtime.list_all() == [stored]
    assert runtime.list_by_organization("ORG-001") == [stored]
    assert runtime.list_by_brand("AI5R") == [stored]
