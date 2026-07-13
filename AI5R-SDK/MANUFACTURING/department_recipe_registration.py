from __future__ import annotations

from typing import Any

from MANUFACTURING import ManufacturingRecipe, ProductionLine
from MANUFACTURING.FACTORY import DigitalFactory

DEPARTMENT_CAPABILITY_ID = "DEPARTMENT_ARTIFACT_GENERATION"

DEPARTMENT_RECIPE = ManufacturingRecipe(
    recipe_id="RCP-DEPARTMENT-001",
    recipe_name="Department Recipe",
    product_type="DEPARTMENT",
    dbom_id="NA-DEPARTMENT",
    production_line_id="LINE-DEPARTMENT-001",
    qa_policy_id="NA-DEPARTMENT",
    packaging_id="NA-DEPARTMENT",
    deployment_id="NA-DEPARTMENT",
)

DEPARTMENT_LINE = ProductionLine(
    line_id="LINE-DEPARTMENT-001",
    line_name="Department Line",
    product_type="DEPARTMENT",
    capability_ids=(DEPARTMENT_CAPABILITY_ID,),
)


def produce_department_artifact(request: Any) -> dict:
    """The capability: creates the Department Artifact data only. No I/O."""

    payload = request.payload
    requirements = payload.get("requirements", {})

    department_name = requirements.get("department_name")
    company_name = requirements.get("company_name")
    parent_department_name = requirements.get("parent_department_name")
    responsibilities = requirements.get("responsibilities", "")
    product_name = payload.get("product_name")

    if not department_name:
        raise ValueError("requirements.department_name is required")

    if not company_name:
        raise ValueError("requirements.company_name is required")

    return {
        **payload,
        "department_artifact": {
            "department": {
                "name": department_name,
                "responsibilities": responsibilities,
            },
            "metadata": {
                "manufacturing_order_id": payload.get("order_id"),
                "recipe_id": payload.get("recipe_id"),
            },
            "relationships": {
                "product": product_name,
                "company": company_name,
                "parent_department": parent_department_name,
            },
        },
    }


def register_department_manufacturing(factory: DigitalFactory) -> None:
    factory.register_capability(DEPARTMENT_CAPABILITY_ID, produce_department_artifact)
    factory.register_recipe(DEPARTMENT_RECIPE, DEPARTMENT_LINE)
