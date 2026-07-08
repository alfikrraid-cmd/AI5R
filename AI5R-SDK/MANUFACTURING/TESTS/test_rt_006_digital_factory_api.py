from MANUFACTURING import (
    DigitalFactory,
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from RUNTIME import RuntimeStatus


def test_digital_factory_is_valid():
    factory = DigitalFactory(
        factory_id="DF-001",
        factory_name="AI5R Digital Factory",
    )

    assert factory.validate() is True


def test_digital_factory_manufactures_product():
    factory = DigitalFactory(
        factory_id="DF-001",
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

    order = ManufacturingOrder(
        order_id="MO-DF-001",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Founder",
        requirements={
            "pages": ["home", "pricing"],
        },
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
        line_name="Website Production Line",
        product_type="WEBSITE",
        station_ids=(
            "REQUIREMENT_ANALYSIS",
            "ARCHITECTURE_DESIGN",
        ),
    )

    response = factory.manufacture(
        order=order,
        recipe=recipe,
        line=line,
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["order_id"] == "MO-DF-001"
    assert response.output["product_name"] == "AI5R Website"
    assert response.output["requirements_analyzed"] is True
    assert response.output["architecture_designed"] is True
    assert response.metadata["factory_id"] == "DF-001"
    assert response.metadata["factory_name"] == "AI5R Digital Factory"


def test_digital_factory_rejects_invalid_factory():
    factory = DigitalFactory(
        factory_id="",
        factory_name="",
    )

    order = ManufacturingOrder(
        order_id="MO-001",
        product_name="Website",
        product_type="WEBSITE",
        requested_by="Founder",
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
        line_name="Website Production Line",
        product_type="WEBSITE",
        station_ids=("REQUIREMENT_ANALYSIS",),
    )

    try:
        factory.manufacture(order, recipe, line)
    except ValueError as exc:
        assert str(exc) == "digital factory is invalid"
    else:
        raise AssertionError("Expected ValueError")
