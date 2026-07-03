from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime


@dataclass
class WarehouseObject:
    id: str
    code: str
    source_type: str
    source_id: str
    object_type: str
    payload: Dict[str, Any]

    status: str = "active"
    version: str = "1.0.0"

    reality_timestamp: Optional[str] = None
    warehouse_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    organization_id: Optional[str] = None
    owner_worker_id: Optional[str] = None

    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    policy_ids: List[str] = field(default_factory=list)

    checksum: Optional[str] = None
    thread_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    def is_valid(self) -> bool:
        return bool(
            self.id
            and self.code
            and self.source_type
            and self.source_id
            and self.object_type
            and isinstance(self.payload, dict)
        )
