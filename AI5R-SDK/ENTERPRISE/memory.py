"""
AI5R Memory Framework
EL-006

Stores operational experience for AI5R Enterprise.

Memory is not approved knowledge.
Memory is raw or semi-structured experience that can later be processed
by Knowledge Factory into reusable Knowledge Warehouse assets.
"""

from typing import Dict, List, Optional

from ENTERPRISE.enterprise_object import EnterpriseObject


class Memory:
    def __init__(self, memory_type: str):
        self.memory_type = memory_type
        self.entries: Dict[str, EnterpriseObject] = {}

    def remember(self, entry: EnterpriseObject) -> EnterpriseObject:
        if entry.type != self.memory_type:
            raise ValueError(
                f"Invalid memory entry type: expected {self.memory_type}, got {entry.type}"
            )

        if entry.code in self.entries:
            raise ValueError(f"Memory entry already exists: {entry.code}")

        self.entries[entry.code] = entry
        return entry

    def recall(self, code: str) -> Optional[EnterpriseObject]:
        return self.entries.get(code)

    def list(self) -> List[EnterpriseObject]:
        return list(self.entries.values())

    def search_by_tag(self, tag: str) -> List[EnterpriseObject]:
        return [entry for entry in self.entries.values() if tag in entry.tags]

    def mark_processed(self, code: str) -> EnterpriseObject:
        entry = self.recall(code)

        if entry is None:
            raise KeyError(f"Memory entry not found: {code}")

        entry.update_status("processed")
        return entry

    def archive(self, code: str) -> EnterpriseObject:
        entry = self.recall(code)

        if entry is None:
            raise KeyError(f"Memory entry not found: {code}")

        entry.update_status("archived")
        return entry

    def to_dict(self) -> Dict:
        return {
            "memory_type": self.memory_type,
            "count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries.values()],
        }
