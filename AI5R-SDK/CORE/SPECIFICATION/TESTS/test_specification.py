import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from CORE.SPECIFICATION import (
    Specification,
    SpecificationStatus,
)


def test_specification_lifecycle():

    specification = Specification(
        specification_type="ORGANIZATION",
        specification_name="Restaurant Organization",
    )

    assert specification.status == SpecificationStatus.DRAFT

    specification.approve()
    assert specification.status == SpecificationStatus.APPROVED

    specification.freeze()
    assert specification.status == SpecificationStatus.FROZEN

    specification.deprecate()
    assert specification.status == SpecificationStatus.DEPRECATED

    assert specification.specification_id.startswith("SPEC-")
