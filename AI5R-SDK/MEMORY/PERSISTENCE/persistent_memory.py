from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class MemoryRecord:
    memory_id: str
    employee_id: str
    version: int
    content: dict
    created_at: str


class PersistentMemoryStore:
    def __init__(self):
        self._store: dict[str, list[MemoryRecord]] = {}

    def write(self, employee_id: str, content: dict) -> MemoryRecord:
        memory_id = str(uuid.uuid4())
        versions = self._store.get(employee_id, [])

        version = len(versions) + 1

        record = MemoryRecord(
            memory_id=memory_id,
            employee_id=employee_id,
            version=version,
            content=content,
            created_at=datetime.now(UTC).isoformat(),
        )

        self._store.setdefault(employee_id, []).append(record)

        return record

    def latest(self, employee_id: str) -> MemoryRecord | None:
        records = self._store.get(employee_id, [])
        return records[-1] if records else None

    def history(self, employee_id: str) -> list[MemoryRecord]:
        return list(self._store.get(employee_id, []))

    def snapshot(self):
        return {
            emp: [
                {
                    "memory_id": r.memory_id,
                    "version": r.version,
                    "content": r.content,
                }
                for r in records
            ]
            for emp, records in self._store.items()
        }
