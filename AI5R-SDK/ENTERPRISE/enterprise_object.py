"""
AI5R Enterprise Object Contract
EL-002

Normalized under AX-004 Universal Object Contract.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from ARCHITECTURE.universal_object import UniversalObject


class EnterpriseObject(UniversalObject):
    def __init__(
        self,
        code: str,
        name: str,
        type: str,
        owner: str = "AI5R",
        version: str = "1.0.0",
        status: str = "active",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        id: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ):
        now = datetime.utcnow().isoformat()

        super().__init__(
            id=id or str(uuid4()),
            code=code,
            name=name,
            type=type,
            version=version,
            status=status,
            owner=owner,
            created_at=created_at or now,
            updated_at=updated_at or now,
            tags=tags or [],
            metadata=metadata or {},
        )

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
