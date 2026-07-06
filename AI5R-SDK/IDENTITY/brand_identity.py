from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class BrandIdentity:

    organization_id: str

    brand_name: str

    tagline: str

    voice: str

    tone: str

    personality_traits: list[str]

    communication_principles: list[str]

    object_type: str = "BRAND_IDENTITY"

    status: str = "ACTIVE"

    brand_identity_id: str = field(
        default_factory=lambda: f"BRAND-{uuid4()}"
    )
