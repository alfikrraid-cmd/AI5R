from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class IdentityObject:

    organization_id: str

    identity_name: str

    vision: str

    mission: str

    values: list[str]

    culture: str

    personality: str

    communication_style: str

    brand: str

    object_type: str = "IDENTITY"

    status: str = "ACTIVE"

    identity_id: str = field(
        default_factory=lambda: f"ID-{uuid4()}"
    )
