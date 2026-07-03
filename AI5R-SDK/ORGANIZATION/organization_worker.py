from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4


@dataclass
class OrganizationWorker:
    organization_id: str
    worker_code: str
    worker_name: str
    worker_type: str
    department_id: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "ORGANIZATION_WORKER"
    worker_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return self.__dict__
