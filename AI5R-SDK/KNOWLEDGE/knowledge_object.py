from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4


@dataclass
class KnowledgeObject:
    organization_id: str
    knowledge_code: str
    title: str
    content: str
    source_type: str

    department_id: Optional[str] = None
    owner_worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "KNOWLEDGE"
    knowledge_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return self.__dict__
