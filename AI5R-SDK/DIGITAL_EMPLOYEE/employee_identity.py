from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class EmployeeIdentity:
    employee_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    organization: str = ""
    department: str = ""
    position: str = ""
    supervisor: str = ""
    version: str = "1.0"
