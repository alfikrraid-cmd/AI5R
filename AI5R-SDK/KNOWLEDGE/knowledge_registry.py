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

    def list_by_organization(self, organization_id):
        return [
            knowledge
            for knowledge in self._knowledge.values()
            if getattr(knowledge, "organization_id", None) == organization_id
        ]

    def list_by_department(self, department_id):
        return [
            knowledge
            for knowledge in self._knowledge.values()
            if getattr(knowledge, "department_id", None) == department_id
        ]

    def list_by_domain(self, domain):
        return [
            knowledge
            for knowledge in self._knowledge.values()
            if getattr(knowledge, "domain", None) == domain
        ]

    def list_by_tag(self, tag):
        return [
            knowledge
            for knowledge in self._knowledge.values()
            if tag in getattr(knowledge, "tags", [])
        ]
