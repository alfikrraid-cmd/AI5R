import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from IDENTITY.organization_identity import OrganizationIdentity


def test_organization_identity():

    org = OrganizationIdentity(
        organization_id="ORG-001",
        organization_name="AI5R",
        industry="Enterprise AI",
        vision="Build Digital Organizations",
        mission="Create trustworthy digital employees",
        core_values=[
            "Integrity",
            "Evidence",
            "Long-term Thinking",
        ],
        culture="Engineering First",
        strategic_priorities=[
            "Innovation",
            "Reliability",
        ],
        risk_appetite="MEDIUM",
        decision_style="EVIDENCE_FIRST",
    )

    assert org.object_type == "ORGANIZATION_IDENTITY"
    assert org.status == "ACTIVE"
    assert org.organization_name == "AI5R"
    assert org.industry == "Enterprise AI"
    assert org.decision_style == "EVIDENCE_FIRST"
    assert org.organization_identity_id.startswith("ORGID-")
