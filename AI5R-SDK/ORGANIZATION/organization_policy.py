from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4


@dataclass
class OrganizationPolicy:
    organization_id: str
    policy_code: str
    policy_name: str
    rules: Dict[str, Any]
    department_id: Optional[str] = None

    object_type: str = "ORGANIZATION_POLICY"
    policy_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return self.__dict__
