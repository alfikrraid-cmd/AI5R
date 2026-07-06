import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from IDENTITY.brand_identity import BrandIdentity


def test_brand_identity():

    brand = BrandIdentity(
        organization_id="ORG-001",
        brand_name="AI5R",
        tagline="Enterprise Digital Organization Platform",
        voice="Executive",
        tone="Professional",
        personality_traits=[
            "Analytical",
            "Trustworthy",
            "Objective",
        ],
        communication_principles=[
            "Evidence First",
            "No Hallucination",
            "Long-term Thinking",
        ],
    )

    assert brand.object_type == "BRAND_IDENTITY"
    assert brand.status == "ACTIVE"
    assert brand.brand_name == "AI5R"
    assert brand.voice == "Executive"
    assert brand.brand_identity_id.startswith("BRAND-")
