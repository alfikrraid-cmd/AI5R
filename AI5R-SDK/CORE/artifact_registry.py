from CORE.artifact import Artifact


class ArtifactRegistry:

    def __init__(self):
        self._artifacts = {}

    def register(self, artifact: Artifact):

        artifact.register()

        self._artifacts[artifact.artifact_id] = artifact

        return {
            "status": "REGISTERED",
            "artifact_id": artifact.artifact_id,
            "artifact": artifact,
        }

    def get(self, artifact_id: str):
        return self._artifacts.get(artifact_id)

    def list_all(self):
        return list(self._artifacts.values())

    def list_by_type(self, artifact_type: str):
        return [
            artifact
            for artifact in self._artifacts.values()
            if artifact.artifact_type == artifact_type
        ]

    def list_by_status(self, status):
        return [
            artifact
            for artifact in self._artifacts.values()
            if artifact.status == status
        ]
