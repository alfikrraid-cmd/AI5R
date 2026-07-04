from typing import Dict

from .memory_object import MemoryObject


class MemoryRegistry:
    """
    Canonical Enterprise Memory Registry.
    """

    def __init__(self):
        self._memory: Dict[str, MemoryObject] = {}

    def register(self, memory: MemoryObject):

        if memory.memory_id in self._memory:
            raise ValueError("Memory already registered")

        self._memory[memory.memory_id] = memory

    def get(self, memory_id: str):

        return self._memory.get(memory_id)

    def list(self):

        return list(self._memory.values())

    def count(self):

        return len(self._memory)
