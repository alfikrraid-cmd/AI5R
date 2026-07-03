from typing import Dict, List, Optional
from .knowledge_source import KnowledgeSource


class KnowledgeSourceRegistry:
    def __init__(self):
        self.sources: Dict[str, KnowledgeSource] = {}

    def register(self, source: KnowledgeSource) -> KnowledgeSource:
        if source.source_id in self.sources:
            raise ValueError("Knowledge source already registered")

        self.sources[source.source_id] = source
        return source

    def get(self, source_id: str) -> Optional[KnowledgeSource]:
        return self.sources.get(source_id)

    def list_by_organization(self, organization_id: str) -> List[KnowledgeSource]:
        return [
            source for source in self.sources.values()
            if source.organization_id == organization_id
        ]

    def list_by_department(self, department_id: str) -> List[KnowledgeSource]:
        return [
            source for source in self.sources.values()
            if source.department_id == department_id
        ]

    def find_by_type(self, source_type: str) -> List[KnowledgeSource]:
        return [
            source for source in self.sources.values()
            if source.source_type == source_type
        ]
