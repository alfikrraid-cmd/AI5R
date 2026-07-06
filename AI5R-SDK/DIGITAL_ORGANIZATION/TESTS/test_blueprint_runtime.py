import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import OrganizationBlueprint, BlueprintRuntime


def test_blueprint_runtime():

    blueprint = OrganizationBlueprint(
        blueprint_name="Restaurant Blueprint",
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
            "Launch Campaign",
            "Daily Sales Review",
        ],
    )

    runtime = BlueprintRuntime()

    registration = runtime.register(blueprint)

    assert registration["status"] == "REGISTERED"
    assert blueprint.blueprint_id.startswith("BP-")
    assert runtime.get(blueprint.blueprint_id) == blueprint

    deployment = runtime.deploy(
        blueprint_id=blueprint.blueprint_id,
        organization_name="AI Restaurant",
    )

    organization_runtime = deployment["organization_runtime"]

    assert deployment["status"] == "DEPLOYED"
    assert deployment["blueprint"].status == "DEPLOYED"
    assert organization_runtime.status()["organization"] == "AI Restaurant"
    assert organization_runtime.status()["departments"] == 4
