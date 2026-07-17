from __future__ import annotations

from typing import Any

from MANUFACTURING import ManufacturingRecipe, ProductionLine
from MANUFACTURING.FACTORY import DigitalFactory

COMPANY_CAPABILITY_ID = "COMPANY_ARTIFACT_GENERATION"

COMPANY_RECIPE = ManufacturingRecipe(
    recipe_id="RCP-COMPANY-001",
    recipe_name="Company Recipe",
    product_type="COMPANY",
    dbom_id="NA-COMPANY",
    production_line_id="LINE-COMPANY-001",
    qa_policy_id="NA-COMPANY",
    packaging_id="NA-COMPANY",
    deployment_id="NA-COMPANY",
)

COMPANY_LINE = ProductionLine(
    line_id="LINE-COMPANY-001",
    line_name="Company Line",
    product_type="COMPANY",
    capability_ids=(COMPANY_CAPABILITY_ID,),
)


def produce_company_artifact(request: Any) -> dict:
    """The capability: creates the Company Artifact data only. No I/O."""

    payload = request.payload
    requirements = payload.get("requirements", {})

    company_name = requirements.get("company_name")
    product_name = payload.get("product_name")

    if not company_name:
        raise ValueError("requirements.company_name is required")

    return {
        **payload,
        "company_artifact": {
            "company": {
                "name": company_name,
                "status": "ACTIVE",
            },
            "metadata": {
                "manufacturing_order_id": payload.get("order_id"),
                "recipe_id": payload.get("recipe_id"),
            },
            "relationships": {
                "product": product_name,
            },
        },
    }


def register_company_manufacturing(factory: DigitalFactory) -> None:
    factory.register_capability(COMPANY_CAPABILITY_ID, produce_company_artifact)
    factory.register_recipe(COMPANY_RECIPE, COMPANY_LINE)
