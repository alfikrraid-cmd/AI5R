from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class RoleObject:

    role_name: str

    organization_level: int

    authority_level: int

    reasoning_depth: int

    risk_weight: float

    mission_weight: float

    policy_weight: float

    knowledge_scope: str

    execution_permission: str

    response_style: str

    object_type: str = "ROLE"

    role_id: str = field(
        default_factory=lambda: f"ROLE-{uuid4()}"
    )

    status: str = "ACTIVE"
