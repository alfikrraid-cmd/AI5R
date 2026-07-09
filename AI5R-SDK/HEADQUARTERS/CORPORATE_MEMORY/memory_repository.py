from HEADQUARTERS.CORPORATE_MEMORY.memory_object import MemoryObject
from HEADQUARTERS.CORPORATE_MEMORY.memory_query import MemoryQuery
from HEADQUARTERS.CORPORATE_MEMORY.memory_registry import MemoryRegistry


class MemoryRepository:
    def __init__(self, registry: MemoryRegistry | None = None) -> None:
        self.registry = registry or MemoryRegistry()
        self.query = MemoryQuery(self.registry)

    def save(self, memory: MemoryObject) -> MemoryObject:
        return self.registry.register(memory)

    def get(self, memory_id: str) -> MemoryObject:
        return self.registry.get(memory_id)

    def snapshot(self) -> list[dict]:
        return self.registry.snapshot()
