from MANUFACTURING import (
    ManufacturingObjectType,
    ManufacturingRecipe,
)


def test_recipe_is_valid():
    recipe = ManufacturingRecipe(
        recipe_id="RCP-001",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-WEB",
        production_line_id="LINE-WEB",
        qa_policy_id="QA-WEB",
        packaging_id="PKG-WEB",
        deployment_id="DEPLOY-WEB",
    )

    assert recipe.validate() is True


def test_recipe_reuses_manufacturing_object():
    recipe = ManufacturingRecipe(
        recipe_id="RCP-002",
        recipe_name="ERP Recipe",
        product_type="ERP",
        dbom_id="DBOM-ERP",
        production_line_id="LINE-ERP",
        qa_policy_id="QA-ERP",
        packaging_id="PKG-ERP",
        deployment_id="DEPLOY-ERP",
    )

    obj = recipe.to_manufacturing_object()

    assert obj.object_type == ManufacturingObjectType.RECIPE
    assert obj.object_id == "RCP-002"
    assert obj.name == "ERP Recipe"


def test_recipe_requires_dbom():
    recipe = ManufacturingRecipe(
        recipe_id="RCP-003",
        recipe_name="AI Recipe",
        product_type="AI_AGENT",
        dbom_id="",
        production_line_id="LINE-AI",
        qa_policy_id="QA-AI",
        packaging_id="PKG-AI",
        deployment_id="DEPLOY-AI",
    )

    assert recipe.validate() is False


def test_recipe_is_ready():
    recipe = ManufacturingRecipe(
        recipe_id="RCP-004",
        recipe_name="Presentation Recipe",
        product_type="PRESENTATION",
        dbom_id="DBOM-PPT",
        production_line_id="LINE-PPT",
        qa_policy_id="QA-PPT",
        packaging_id="PKG-PPT",
        deployment_id="DEPLOY-PPT",
    )

    assert recipe.is_ready() is True
