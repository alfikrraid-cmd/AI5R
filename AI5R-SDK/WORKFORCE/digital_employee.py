from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class DigitalEmployee:

    employee_name: str

    organization_id: str

    identity_id: str

    position_id: str

    kernel_id: str

    capability_ids: list[str] = field(default_factory=list)

    cognitive_function_ids: list[str] = field(default_factory=list)

    status: str = "ACTIVE"

    employment_type: str = "FULL_TIME"

    metadata: dict[str, Any] = field(default_factory=dict)

    object_type: str = "DIGITAL_EMPLOYEE"

    employee_id: str = field(
        default_factory=lambda: f"EMP-{uuid4()}"
    )
