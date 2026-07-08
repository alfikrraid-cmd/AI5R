from MANUFACTURING import (
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import (
    DigitalFactory,
    FactoryRegistry,
)


def test_factory_registry_registers_recipe_and_line():
    registry = FactoryRegistry()

    recipe = ManufacturingRecipe(
        recipe_id="RCP-WEB-011",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-WEB-011",
        production_line_id="LINE-WEB-011",
        qa_policy_id="QA-WEB-011",
        packaging_id="PKG-WEB-011",
        deployment_id="DEPLOY-WEB-011",
    )

    line = ProductionLine(
        line_id="LINE-WEB-011",
        line_name="Website Line",
        product_type="WEBSITE",
        capability_ids=("REQUIREMENT_ANALYSIS",),
    )

    registry.register_recipe(recipe, line)

    assert registry.get_recipe("WEBSITE") == recipe
    assert registry.get_line("LINE-WEB-011") == line
    assert registry.recipe_count() == 1
    assert registry.line_count() == 1


def test_factory_uses_registry_for_recipe_lookup():
    factory = DigitalFactory(
        factory_id="DF-011",
        factory_name="AI5R Digital Factory",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-AI-011",
        recipe_name="AI Agent Recipe",
        product_type="AI_AGENT",
        dbom_id="DBOM-AI-011",
        production_line_id="LINE-AI-011",
        qa_policy_id="QA-AI-011",
        packaging_id="PKG-AI-011",
        deployment_id="DEPLOY-AI-011",
    )

    line = ProductionLine(
        line_id="LINE-AI-011",
        line_name="AI Agent Line",
        product_type="AI_AGENT",
        capability_ids=("PROMPT_DESIGN",),
    )

    factory.register_recipe(recipe, line)

    assert factory.get_recipe("AI_AGENT") == recipe
    assert factory.get_line("LINE-AI-011") == line
    assert factory.registry.recipe_count() == 1
    assert factory.registry.line_count() == 1


def test_factory_registry_rejects_recipe_line_mismatch():
    registry = FactoryRegistry()

    recipe = ManufacturingRecipe(
        recipe_id="RCP-WEB",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-WEB",
        production_line_id="LINE-WEB",
        qa_policy_id="QA-WEB",
        packaging_id="PKG-WEB",
        deployment_id="DEPLOY-WEB",
    )

    line = ProductionLine(
        line_id="LINE-ERP",
        line_name="ERP Line",
        product_type="WEBSITE",
        capability_ids=("REQUIREMENT_ANALYSIS",),
    )

    try:
        registry.register_recipe(recipe, line)
    except ValueError as exc:
        assert str(exc) == "recipe and production line mismatch"
    else:
        raise AssertionError("Expected ValueError")
