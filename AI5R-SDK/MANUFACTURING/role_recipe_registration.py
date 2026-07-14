from __future__ import annotations

from typing import Any

from MANUFACTURING import ManufacturingRecipe, ProductionLine
from MANUFACTURING.FACTORY import DigitalFactory

ROLE_CAPABILITY_ID = "ROLE_ARTIFACT_GENERATION"

ROLE_RECIPE = ManufacturingRecipe(
    recipe_id="RCP-ROLE-001",
    recipe_name="Role Recipe",
    product_type="ROLE",
    dbom_id="NA-ROLE",
    production_line_id="LINE-ROLE-001",
    qa_policy_id="NA-ROLE",
    packaging_id="NA-ROLE",
    deployment_id="NA-ROLE",
)

ROLE_LINE = ProductionLine(
    line_id="LINE-ROLE-001",
    line_name="Role Line",
    product_type="ROLE",
    capability_ids=(ROLE_CAPABILITY_ID,),
)


def produce_role_artifact(request: Any) -> dict:
    """The capability: creates the Role Artifact data only. No I/O."""

    payload = request.payload
    requirements = payload.get("requirements", {})

    role_name = requirements.get("role_name")
    department_name = requirements.get("department_name")
    reports_to_role_name = requirements.get("reports_to_role_name")
    responsibilities = requirements.get("responsibilities", "")
    goals = requirements.get("goals", "")
    permissions = requirements.get("permissions", "")
    product_name = payload.get("product_name")

    if not role_name:
        raise ValueError("requirements.role_name is required")

    if not department_name:
        raise ValueError("requirements.department_name is required")

    return {
        **payload,
        "role_artifact": {
            "role": {
                "name": role_name,
                "responsibilities": responsibilities,
                "goals": goals,
                "permissions": permissions,
            },
            "metadata": {
                "manufacturing_order_id": payload.get("order_id"),
                "recipe_id": payload.get("recipe_id"),
            },
            "relationships": {
                "product": product_name,
                "department": department_name,
                "reports_to_role": reports_to_role_name,
            },
        },
    }


def register_role_manufacturing(factory: DigitalFactory) -> None:
    factory.register_capability(ROLE_CAPABILITY_ID, produce_role_artifact)
    factory.register_recipe(ROLE_RECIPE, ROLE_LINE)
