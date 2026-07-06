from __future__ import annotations


class MemoryIndex:
    def __init__(self):
        self.index: dict[str, list[str]] = {}

    def add(self, employee_id: str, memory_id: str):
        self.index.setdefault(employee_id, []).append(memory_id)

    def search(self, employee_id: str) -> list[str]:
        return self.index.get(employee_id, [])
