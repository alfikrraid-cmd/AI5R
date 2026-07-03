from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4


@dataclass
class DepartmentObject:
    organization_id: str
    department_code: str
    department_name: str
    parent_department_id: Optional[str] = None
    policies: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "DEPARTMENT"
    department_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__
