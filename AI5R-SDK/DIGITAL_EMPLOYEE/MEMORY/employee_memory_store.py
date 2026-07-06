from __future__ import annotations

from typing import Any

from .employee_memory import EmployeeMemory


class EmployeeMemoryStore:
    def __init__(self) -> None:
        self._memories: dict[str, EmployeeMemory] = {}
        self._employee_index: dict[str, list[str]] = {}

    def store(
        self,
        employee_id: str,
        memory_type: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> EmployeeMemory:
        memory = EmployeeMemory(
            employee_id=employee_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
        )

        self._memories[memory.memory_id] = memory
        self._employee_index.setdefault(employee_id, []).append(memory.memory_id)

        return memory

    def get(self, memory_id: str) -> EmployeeMemory | None:
        return self._memories.get(memory_id)

    def require(self, memory_id: str) -> EmployeeMemory:
        memory = self.get(memory_id)
        if memory is None:
            raise KeyError(f"Employee memory not found: {memory_id}")
        return memory

    def list(self, employee_id: str) -> list[EmployeeMemory]:
        return [
            self._memories[memory_id]
            for memory_id in self._employee_index.get(employee_id, [])
            if memory_id in self._memories
        ]

    def list_by_type(
        self,
        employee_id: str,
        memory_type: str,
    ) -> list[EmployeeMemory]:
        return [
            memory
            for memory in self.list(employee_id)
            if memory.memory_type == memory_type
        ]

    def delete(self, memory_id: str) -> bool:
        memory = self._memories.pop(memory_id, None)

        if memory is None:
            return False

        indexed = self._employee_index.get(memory.employee_id, [])
        self._employee_index[memory.employee_id] = [
            indexed_memory_id
            for indexed_memory_id in indexed
            if indexed_memory_id != memory_id
        ]

        return True

    def count(self, employee_id: str | None = None) -> int:
        if employee_id is None:
            return len(self._memories)

        return len(self.list(employee_id))

    def snapshot(self, employee_id: str | None = None) -> dict[str, Any]:
        if employee_id is not None:
            return {
                "employee_id": employee_id,
                "count": self.count(employee_id),
                "memories": [
                    memory.snapshot()
                    for memory in self.list(employee_id)
                ],
            }

        return {
            "count": self.count(),
            "memories": {
                memory_id: memory.snapshot()
                for memory_id, memory in self._memories.items()
            },
        }
