from typing import Dict, List, Optional
from .knowledge_object import KnowledgeObject


class KnowledgeRegistry:
    def __init__(self):
        self.knowledge: Dict[str, KnowledgeObject] = {}

    def register(self, item: KnowledgeObject) -> KnowledgeObject:
        if item.knowledge_id in self.knowledge:
            raise ValueError("Knowledge already registered")

        self.knowledge[item.knowledge_id] = item
        return item

    def get(self, knowledge_id: str) -> Optional[KnowledgeObject]:
        return self.knowledge.get(knowledge_id)

    def list_by_organization(self, organization_id: str) -> List[KnowledgeObject]:
        return [
            item for item in self.knowledge.values()
            if item.organization_id == organization_id
        ]

    def list_by_department(self, department_id: str) -> List[KnowledgeObject]:
        return [
            item for item in self.knowledge.values()
            if item.department_id == department_id
        ]

    def search(self, organization_id: str, keyword: str) -> List[KnowledgeObject]:
        keyword = keyword.lower()

        return [
            item for item in self.list_by_organization(organization_id)
            if keyword in item.title.lower()
            or keyword in item.content.lower()
            or keyword in item.knowledge_code.lower()
        ]
