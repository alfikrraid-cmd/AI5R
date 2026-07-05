from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class EmploymentContract:

    contract_code: str

    employment_type: str

    working_hours_per_month: int

    managed_by: str

    private_memory: bool

    private_knowledge: bool

    private_kernel: bool

    sla: str

    object_type: str = "EMPLOYMENT_CONTRACT"

    status: str = "ACTIVE"

    contract_id: str = field(
        default_factory=lambda: f"CONTRACT-{uuid4()}"
    )
