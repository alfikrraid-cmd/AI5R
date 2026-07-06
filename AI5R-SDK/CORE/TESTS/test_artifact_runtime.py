import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CORE import ArtifactRuntime, ArtifactStatus


def test_artifact_runtime():

    runtime = ArtifactRuntime()

    result = runtime.manufacture_and_register(
        artifact_type="BLUEPRINT",
        artifact_name="Restaurant Blueprint",
        metadata={
            "owner": "AI5R",
        },
    )

    artifact = result["artifact"]

    assert result["status"] == "MANUFACTURED_AND_REGISTERED"
    assert result["manufacturing"]["status"] == "MANUFACTURED"
    assert result["registration"]["status"] == "REGISTERED"

    assert artifact.status == ArtifactStatus.REGISTERED
    assert artifact.artifact_type == "BLUEPRINT"
    assert artifact.artifact_name == "Restaurant Blueprint"

    assert runtime.get(artifact.artifact_id) == artifact
    assert runtime.list_all() == [artifact]
    assert runtime.list_by_type("BLUEPRINT") == [artifact]
    assert runtime.list_by_status(ArtifactStatus.REGISTERED) == [artifact]
