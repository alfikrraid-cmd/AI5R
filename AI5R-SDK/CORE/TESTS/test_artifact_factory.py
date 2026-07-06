import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CORE import ArtifactFactory, ArtifactStatus


def test_artifact_factory():

    result = ArtifactFactory().manufacture(
        artifact_type="DIGITAL_EMPLOYEE",
        artifact_name="Marketing AI",
        metadata={
            "owner": "AI5R",
        },
    )

    artifact = result["artifact"]

    assert result["status"] == "MANUFACTURED"
    assert artifact.artifact_type == "DIGITAL_EMPLOYEE"
    assert artifact.artifact_name == "Marketing AI"
    assert artifact.status == ArtifactStatus.MANUFACTURED
    assert artifact.metadata["owner"] == "AI5R"
    assert artifact.artifact_id.startswith("ART-")
