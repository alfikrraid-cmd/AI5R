from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class PositionObject:

    organization_id: str

    position_code: str

    position_name: str

    department: str

    reports_to: str | None = None

    authority_level: int = 0

    approval_limit: float = 0.0

    object_type: str = "POSITION"

    status: str = "ACTIVE"

    position_id: str = field(
        default_factory=lambda: f"POS-{uuid4()}"
    )
