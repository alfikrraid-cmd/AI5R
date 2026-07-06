import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import (
    OrganizationFactory,
    OrganizationSpecification,
)


def test_organization_factory_rejects_draft_specification():

    specification = OrganizationSpecification(
        organization_name="AI Restaurant",
        industry="Food and Beverage",
        departments=[
            "Executive",
            "Kitchen",
            "Marketing",
            "Finance",
        ],
        positions=[
            "CEO",
            "Kitchen Manager",
            "Marketing Manager",
            "Finance Manager",
        ],
        capabilities=[
            "Menu Planning",
            "Campaign Planning",
            "Cashflow Analysis",
        ],
    )

    result = OrganizationFactory().manufacture(specification)

    assert result["status"] == "REJECTED"
    assert result["artifact"] is None
    assert result["organization_runtime"] is None


def test_organization_factory_manufactures_approved_specification():

    specification = OrganizationSpecification(
        organization_name="AI Restaurant",
        industry="Food and Beverage",
        departments=[
            "Executive",
            "Kitchen",
            "Marketing",
            "Finance",
        ],
        positions=[
            "CEO",
            "Kitchen Manager",
            "Marketing Manager",
            "Finance Manager",
        ],
        capabilities=[
            "Menu Planning",
            "Campaign Planning",
            "Cashflow Analysis",
        ],
        workflows=[
            "Daily Sales Review",
        ],
    )

    specification.approve()

    result = OrganizationFactory().manufacture(specification)

    runtime = result["organization_runtime"]
    artifact = result["artifact"]

    assert result["status"] == "MANUFACTURED"
    assert artifact.artifact_type == "ORGANIZATION"
    assert artifact.artifact_name == "AI Restaurant"
    assert artifact.metadata["industry"] == "Food and Beverage"
    assert artifact.metadata["specification_id"] == specification.specification_id

    assert runtime.status()["organization"] == "AI Restaurant"
    assert runtime.status()["departments"] == 4
