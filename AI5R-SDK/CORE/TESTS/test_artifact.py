import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CORE import Artifact
from CORE import ArtifactStatus


def test_artifact_lifecycle():

    artifact = Artifact(
        artifact_type="KNOWLEDGE",
        artifact_name="Knowledge Object",
    )

    assert artifact.status == ArtifactStatus.DRAFT

    artifact.manufacture()
    assert artifact.status == ArtifactStatus.MANUFACTURED

    artifact.register()
    assert artifact.status == ArtifactStatus.REGISTERED

    artifact.activate()
    assert artifact.status == ArtifactStatus.ACTIVE

    artifact.deprecate()
    assert artifact.status == ArtifactStatus.DEPRECATED

    artifact.archive()
    assert artifact.status == ArtifactStatus.ARCHIVED

    assert artifact.artifact_id.startswith("ART-")
