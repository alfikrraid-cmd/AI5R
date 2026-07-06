from CORE.artifact_factory import ArtifactFactory
from CORE.artifact_registry import ArtifactRegistry


class ArtifactRuntime:

    def __init__(self):
        self.factory = ArtifactFactory()
        self.registry = ArtifactRegistry()

    def manufacture(
        self,
        artifact_type: str,
        artifact_name: str,
        version: str = "1.0.0",
        metadata: dict | None = None,
    ):

        result = self.factory.manufacture(
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            version=version,
            metadata=metadata or {},
        )

        return result

    def register(self, artifact):
        return self.registry.register(artifact)

    def manufacture_and_register(
        self,
        artifact_type: str,
        artifact_name: str,
        version: str = "1.0.0",
        metadata: dict | None = None,
    ):

        manufactured = self.manufacture(
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            version=version,
            metadata=metadata or {},
        )

        artifact = manufactured["artifact"]

        registration = self.register(artifact)

        return {
            "status": "MANUFACTURED_AND_REGISTERED",
            "artifact": artifact,
            "manufacturing": manufactured,
            "registration": registration,
        }

    def get(self, artifact_id: str):
        return self.registry.get(artifact_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_type(self, artifact_type: str):
        return self.registry.list_by_type(artifact_type)

    def list_by_status(self, status):
        return self.registry.list_by_status(status)
