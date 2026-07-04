from typing import List, Optional

from .memory_object import MemoryObject
from .memory_registry import MemoryRegistry


class MemoryQueryEngine:
    """
    Query engine for Enterprise Memory.
    """

    def __init__(self, registry: MemoryRegistry):
        self.registry = registry

    def by_learning_id(self, learning_id: str) -> List[MemoryObject]:
        return [
            memory
            for memory in self.registry.list()
            if memory.learning_id == learning_id
        ]

    def by_digital_thread_id(
        self,
        digital_thread_id: str,
    ) -> List[MemoryObject]:
        return [
            memory
            for memory in self.registry.list()
            if memory.digital_thread_id == digital_thread_id
        ]

    def by_min_confidence(
        self,
        minimum_confidence: float,
    ) -> List[MemoryObject]:
        return [
            memory
            for memory in self.registry.list()
            if memory.confidence >= minimum_confidence
        ]

    def find(
        self,
        learning_id: Optional[str] = None,
        digital_thread_id: Optional[str] = None,
        minimum_confidence: Optional[float] = None,
    ) -> List[MemoryObject]:

        results = self.registry.list()

        if learning_id is not None:
            results = [
                memory
                for memory in results
                if memory.learning_id == learning_id
            ]

        if digital_thread_id is not None:
            results = [
                memory
                for memory in results
                if memory.digital_thread_id == digital_thread_id
            ]

        if minimum_confidence is not None:
            results = [
                memory
                for memory in results
                if memory.confidence >= minimum_confidence
            ]

        return results
