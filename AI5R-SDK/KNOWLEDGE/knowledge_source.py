from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4


@dataclass
class KnowledgeSource:
    organization_id: str
    source_code: str
    source_name: str
    source_type: str
    source_uri: Optional[str] = None
    department_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "KNOWLEDGE_SOURCE"
    source_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return self.__dict__
