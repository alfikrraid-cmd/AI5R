from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory
from RUNTIME import RuntimeStatus


def test_digital_factory_registers_recipe_and_line():
    factory = DigitalFactory(
        factory_id="DF-010",
        factory_name="AI5R Digital Factory",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-WEB-010",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-WEB-010",
        production_line_id="LINE-WEB-010",
        qa_policy_id="QA-WEB-010",
        packaging_id="PKG-WEB-010",
        deployment_id="DEPLOY-WEB-010",
    )

    line = ProductionLine(
        line_id="LINE-WEB-010",
        line_name="Website Line",
        product_type="WEBSITE",
        capability_ids=("REQUIREMENT_ANALYSIS",),
    )

    factory.register_recipe(recipe, line)

    assert factory.get_recipe("WEBSITE") == recipe
    assert factory.get_line("LINE-WEB-010") == line


def test_digital_factory_manufactures_order_using_registered_recipe():
    factory = DigitalFactory(
        factory_id="DF-010",
        factory_name="AI5R Digital Factory",
    )

    def requirement_analysis(request):
        return {
            **request.payload,
            "requirements_analyzed": True,
        }

    def architecture_design(request):
        return {
            **request.payload,
            "architecture_designed": True,
        }

    factory.register_capability("REQUIREMENT_ANALYSIS", requirement_analysis)
    factory.register_capability("ARCHITECTURE_DESIGN", architecture_design)

    recipe = ManufacturingRecipe(
        recipe_id="RCP-WEB-010",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-WEB-010",
        production_line_id="LINE-WEB-010",
        qa_policy_id="QA-WEB-010",
        packaging_id="PKG-WEB-010",
        deployment_id="DEPLOY-WEB-010",
    )

    line = ProductionLine(
        line_id="LINE-WEB-010",
        line_name="Website Capability Line",
        product_type="WEBSITE",
        capability_ids=(
            "REQUIREMENT_ANALYSIS",
            "ARCHITECTURE_DESIGN",
        ),
    )

    factory.register_recipe(recipe, line)

    order = ManufacturingOrder(
        order_id="MO-WEB-010",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Founder",
    )

    response = factory.manufacture_order(order)

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["order_id"] == "MO-WEB-010"
    assert response.output["product_name"] == "AI5R Website"
    assert response.output["requirements_analyzed"] is True
    assert response.output["architecture_designed"] is True


def test_digital_factory_rejects_missing_recipe_for_order():
    factory = DigitalFactory(
        factory_id="DF-010",
        factory_name="AI5R Digital Factory",
    )

    order = ManufacturingOrder(
        order_id="MO-UNKNOWN",
        product_name="Unknown Product",
        product_type="UNKNOWN",
        requested_by="Founder",
    )

    try:
        factory.manufacture_order(order)
    except ValueError as exc:
        assert str(exc) == "recipe not found for product type: UNKNOWN"
    else:
        raise AssertionError("Expected ValueError")


def test_digital_factory_rejects_recipe_line_product_type_mismatch():
    factory = DigitalFactory(
        factory_id="DF-010",
        factory_name="AI5R Digital Factory",
    )

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
        line_id="LINE-WEB",
        line_name="ERP Line",
        product_type="ERP",
        capability_ids=("REQUIREMENT_ANALYSIS",),
    )

    try:
        factory.register_recipe(recipe, line)
    except ValueError as exc:
        assert str(exc) == "recipe and production line product type mismatch"
    else:
        raise AssertionError("Expected ValueError")
