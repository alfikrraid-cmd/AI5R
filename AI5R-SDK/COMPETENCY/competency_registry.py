class CompetencyRegistry:
    """
    Enterprise Competency Registry

    Objective:
    Store and retrieve measured competency objects.
    """

    def __init__(self):
        self._competencies = {}

    def register(self, competency):
        competency_id = getattr(competency, "competency_id", None)

        if competency_id is None:
            raise ValueError("Competency object must have competency_id")

        self._competencies[competency_id] = competency
        return competency

    def get(self, competency_id):
        return self._competencies.get(competency_id)

    def exists(self, competency_id):
        return competency_id in self._competencies

    def list_all(self):
        return list(self._competencies.values())

    def list_by_organization(self, organization_id):
        return [
            competency
            for competency in self._competencies.values()
            if getattr(competency, "organization_id", None) == organization_id
        ]

    def list_by_capability(self, capability_id):
        return [
            competency
            for competency in self._competencies.values()
            if getattr(competency, "capability_id", None) == capability_id
        ]

    def list_by_status(self, status):
        return [
            competency
            for competency in self._competencies.values()
            if getattr(competency, "status", None) == status
        ]
