import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CORE import Artifact, ArtifactRegistry, ArtifactStatus


def test_artifact_registry():

    registry = ArtifactRegistry()

    artifact = Artifact(
        artifact_type="KNOWLEDGE",
        artifact_name="Knowledge Object",
    )

    result = registry.register(artifact)

    assert result["status"] == "REGISTERED"
    assert artifact.status == ArtifactStatus.REGISTERED
    assert registry.get(artifact.artifact_id) == artifact
    assert registry.list_all() == [artifact]
    assert registry.list_by_type("KNOWLEDGE") == [artifact]
    assert registry.list_by_status(ArtifactStatus.REGISTERED) == [artifact]
