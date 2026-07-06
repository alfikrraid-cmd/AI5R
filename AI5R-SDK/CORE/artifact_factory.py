from CORE.artifact import Artifact


class ArtifactFactory:

    def manufacture(
        self,
        artifact_type: str,
        artifact_name: str,
        version: str = "1.0.0",
        metadata: dict | None = None,
    ):

        artifact = Artifact(
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            version=version,
            metadata=metadata or {},
        )

        artifact.manufacture()

        return {
            "status": "MANUFACTURED",
            "artifact": artifact,
        }
