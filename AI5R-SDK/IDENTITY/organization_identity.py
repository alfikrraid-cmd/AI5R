from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class OrganizationIdentity:

    organization_id: str

    organization_name: str

    industry: str

    vision: str

    mission: str

    core_values: list[str]

    culture: str

    strategic_priorities: list[str]

    risk_appetite: str

    decision_style: str

    object_type: str = "ORGANIZATION_IDENTITY"

    status: str = "ACTIVE"

    organization_identity_id: str = field(
        default_factory=lambda: f"ORGID-{uuid4()}"
    )
