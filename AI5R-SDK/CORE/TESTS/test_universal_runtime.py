import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CORE import UniversalRuntime, ArtifactStatus
from CORE.SPECIFICATION import Specification


def test_universal_runtime_rejects_draft_specification():

    runtime = UniversalRuntime()

    specification = Specification(
        specification_type="ORGANIZATION",
        specification_name="Restaurant Organization",
    )

    result = runtime.manufacture_and_register(specification)

    assert result["status"] == "REJECTED"
    assert result["artifact"] is None
    assert result["registration"] is None


def test_universal_runtime_manufactures_and_registers():

    runtime = UniversalRuntime()

    specification = Specification(
        specification_type="ORGANIZATION",
        specification_name="Restaurant Organization",
        metadata={
            "industry": "Food and Beverage",
        },
    )

    specification.approve()

    result = runtime.manufacture_and_register(specification)

    artifact = result["artifact"]

    assert result["status"] == "MANUFACTURED_AND_REGISTERED"
    assert result["manufacturing"]["status"] == "MANUFACTURED"
    assert result["registration"]["status"] == "REGISTERED"

    assert artifact.status == ArtifactStatus.REGISTERED
    assert artifact.metadata["specification_id"] == specification.specification_id

    assert runtime.get(artifact.artifact_id) == artifact
    assert runtime.list_all() == [artifact]
    assert runtime.list_by_type("ORGANIZATION") == [artifact]
    assert runtime.list_by_status(ArtifactStatus.REGISTERED) == [artifact]
