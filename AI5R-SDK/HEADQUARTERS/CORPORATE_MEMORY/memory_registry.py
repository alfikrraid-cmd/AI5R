from HEADQUARTERS.CORPORATE_MEMORY.memory_object import MemoryObject


class MemoryRegistry:
    def __init__(self) -> None:
        self._memories: dict[str, MemoryObject] = {}

    def register(self, memory: MemoryObject) -> MemoryObject:
        self._memories[memory.memory_id] = memory
        return memory

    def get(self, memory_id: str) -> MemoryObject:
        if memory_id not in self._memories:
            raise KeyError(f"Memory not found: {memory_id}")
        return self._memories[memory_id]

    def all(self) -> list[MemoryObject]:
        return list(self._memories.values())

    def snapshot(self) -> list[dict]:
        return [memory.snapshot() for memory in self.all()]
