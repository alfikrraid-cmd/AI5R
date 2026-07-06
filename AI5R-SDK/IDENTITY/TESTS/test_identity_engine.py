import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from IDENTITY.identity_object import IdentityObject
from IDENTITY.identity_engine import IdentityEngine


def test_identity_engine():

    engine = IdentityEngine()

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

    result = engine.build(identity)

    assert result["status"] == "READY"
    assert result["identity"] == identity
    assert result["profile"]["brand"] == "AI5R"
    assert result["profile"]["communication_style"] == "Executive"
