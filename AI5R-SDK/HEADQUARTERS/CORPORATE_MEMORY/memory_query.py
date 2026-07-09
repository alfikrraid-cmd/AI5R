from HEADQUARTERS.CORPORATE_MEMORY.memory_registry import MemoryRegistry


class MemoryQuery:
    def __init__(self, registry: MemoryRegistry) -> None:
        self.registry = registry

    def by_mission_id(self, mission_id: str) -> list[dict]:
        return [
            memory.snapshot()
            for memory in self.registry.all()
            if memory.mission_id == mission_id
        ]

    def by_executive(self, executive: str) -> list[dict]:
        return [
            memory.snapshot()
            for memory in self.registry.all()
            if memory.executive == executive
        ]

    def search_title(self, keyword: str) -> list[dict]:
        resolved = keyword.lower()
        return [
            memory.snapshot()
            for memory in self.registry.all()
            if resolved in memory.mission_title.lower()
        ]
