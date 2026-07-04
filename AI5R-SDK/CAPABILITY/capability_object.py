from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any
from uuid import uuid4


@dataclass
class CapabilityObject:
    """
    Enterprise Capability Object

    Represents an executable enterprise capability.
    """

    organization_id: str

    capability_code: str

    capability_name: str

    description: str

    supported_domains: List[str] = field(default_factory=list)

    required_knowledge_ids: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "CAPABILITY"

    capability_id: str = field(default_factory=lambda: str(uuid4()))

    status: str = "ACTIVE"

    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def to_dict(self):
        return self.__dict__
