from typing import Any

from INTELLIGENCE.KNOWLEDGE.GRAPH.knowledge_graph import KnowledgeGraph
from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject


class KnowledgeGraphQueryEngine:
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def get(self, knowledge_id: str) -> KnowledgeObject | None:
        return self.graph.nodes.get(knowledge_id)

    def by_domain(self, domain: str) -> list[KnowledgeObject]:
        ids = self.graph.domain_index().get(domain, [])
        return [self.graph.nodes[item] for item in ids]

    def by_priority(self, priority_level: str) -> list[KnowledgeObject]:
        ids = self.graph.priority_index().get(priority_level, [])
        return [self.graph.nodes[item] for item in ids]

    def related_to(self, knowledge_id: str) -> list[KnowledgeObject]:
        ids = self.graph.neighbors(knowledge_id)
        return [
            self.graph.nodes[item]
            for item in ids
            if item in self.graph.nodes
        ]

    def conflicts_for(self, knowledge_id: str) -> list[dict[str, Any]]:
        return self.graph.conflict_index().get(knowledge_id, [])

    def high_value(self) -> list[KnowledgeObject]:
        result: list[KnowledgeObject] = []

        for level in ["CRITICAL", "HIGH"]:
            result.extend(self.by_priority(level))

        return result

    def search_summary(self, keyword: str) -> list[KnowledgeObject]:
        if not keyword:
            raise ValueError("keyword is required")

        keyword = keyword.lower()

        return [
            obj
            for obj in self.graph.nodes.values()
            if keyword in obj.summary.lower()
        ]
