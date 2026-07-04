class KnowledgeRegistry:
    """
    Registry for Knowledge Objects.

    Objective:
    Store and retrieve knowledge objects without redesigning KnowledgeObject.
    """

    def __init__(self):
        self._knowledge = {}

    def register(self, knowledge):
        knowledge_id = getattr(knowledge, "knowledge_id", None)

        if knowledge_id is None:
            raise ValueError("Knowledge object must have knowledge_id")

        self._knowledge[knowledge_id] = knowledge
        return knowledge

    def get(self, knowledge_id):
        return self._knowledge.get(knowledge_id)

    def list_all(self):
        return list(self._knowledge.values())

    def exists(self, knowledge_id):
        return knowledge_id in self._knowledge
