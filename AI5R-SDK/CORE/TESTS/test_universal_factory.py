import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CORE import UniversalFactory, ArtifactStatus
from CORE.SPECIFICATION import Specification


def test_universal_factory_rejects_draft_specification():

    specification = Specification(
        specification_type="ORGANIZATION",
        specification_name="Restaurant Organization",
    )

    result = UniversalFactory().manufacture(specification)

    assert result["status"] == "REJECTED"
    assert result["artifact"] is None


def test_universal_factory_manufactures_from_approved_specification():

    specification = Specification(
        specification_type="ORGANIZATION",
        specification_name="Restaurant Organization",
        metadata={
            "industry": "Food and Beverage",
        },
    )

    specification.approve()

    result = UniversalFactory().manufacture(specification)

    artifact = result["artifact"]

    assert result["status"] == "MANUFACTURED"
    assert artifact.artifact_type == "ORGANIZATION"
    assert artifact.artifact_name == "Restaurant Organization"
    assert artifact.status == ArtifactStatus.MANUFACTURED
    assert artifact.metadata["specification_id"] == specification.specification_id
    assert artifact.metadata["industry"] == "Food and Beverage"
