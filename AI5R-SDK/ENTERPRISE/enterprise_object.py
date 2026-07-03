"""
AI5R Enterprise Object Contract
EL-002

Defines the common identity contract for all enterprise objects
in AI5R Generation 2.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class EnterpriseObject:
    code: str
    name: str
    type: str
    owner: str = "AI5R"
    version: str = "1.0.0"
    status: str = "active"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def update_status(self, status: str) -> None:
        self.status = status
        self.touch()

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)
            self.touch()

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "type": self.type,
            "version": self.version,
            "status": self.status,
            "owner": self.owner,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "metadata": self.metadata,
        }
