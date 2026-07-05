from dataclasses import dataclass, field
from typing import Any

from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject


@dataclass
class KnowledgeGraph:
    nodes: dict[str, KnowledgeObject] = field(default_factory=dict)
    edges: list[dict[str, Any]] = field(default_factory=list)

    def add_node(self, knowledge: KnowledgeObject) -> None:
        knowledge.validate()
        self.nodes[knowledge.knowledge_id] = knowledge

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        confidence: float = 1.0,
    ) -> None:
        self.edges.append({
            "source": source_id,
            "target": target_id,
            "relationship": relationship,
            "confidence": confidence,
        })

    def build(self, knowledge_objects: list[KnowledgeObject]) -> "KnowledgeGraph":
        for obj in knowledge_objects:
            self.add_node(obj)

            for relation in obj.relationships:
                self.add_edge(
                    source_id=obj.knowledge_id,
                    target_id=relation["target_id"],
                    relationship=relation["relationship"],
                    confidence=relation.get("confidence", 1.0),
                )

        return self

    def neighbors(self, knowledge_id: str) -> list[str]:
        return [
            edge["target"]
            for edge in self.edges
            if edge["source"] == knowledge_id
        ]

    def domain_index(self) -> dict[str, list[str]]:
        index: dict[str, list[str]] = {}

        for obj in self.nodes.values():
            domain = obj.classification.get("domain", "general")
            index.setdefault(domain, []).append(obj.knowledge_id)

        return index

    def priority_index(self) -> dict[str, list[str]]:
        index: dict[str, list[str]] = {}

        for obj in self.nodes.values():
            level = obj.priority.get("priority_level", "UNKNOWN")
            index.setdefault(level, []).append(obj.knowledge_id)

        return index

    def conflict_index(self) -> dict[str, list[dict]]:
        conflicts: dict[str, list[dict]] = {}

        for obj in self.nodes.values():
            conflicts[obj.knowledge_id] = obj.conflicts

        return conflicts

    def statistics(self) -> dict[str, int]:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
        }
