from CORE.artifact_registry import ArtifactRegistry
from CORE.universal_factory import UniversalFactory


class UniversalRuntime:

    def __init__(self):
        self.factory = UniversalFactory()
        self.registry = ArtifactRegistry()

    def manufacture(self, specification):
        return self.factory.manufacture(specification)

    def manufacture_and_register(self, specification):

        manufactured = self.manufacture(specification)

        if manufactured["status"] != "MANUFACTURED":
            return {
                "status": "REJECTED",
                "reason": manufactured.get("reason"),
                "manufacturing": manufactured,
                "registration": None,
                "artifact": None,
            }

        artifact = manufactured["artifact"]
        registration = self.registry.register(artifact)

        return {
            "status": "MANUFACTURED_AND_REGISTERED",
            "manufacturing": manufactured,
            "registration": registration,
            "artifact": artifact,
        }

    def get(self, artifact_id: str):
        return self.registry.get(artifact_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_type(self, artifact_type: str):
        return self.registry.list_by_type(artifact_type)

    def list_by_status(self, status):
        return self.registry.list_by_status(status)
