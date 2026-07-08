from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory
from RUNTIME import RuntimeStatus


def test_digital_factory_end_to_end_manufacturing_flow():
    factory = DigitalFactory(
        factory_id="DF-E2E-001",
        factory_name="AI5R Digital Factory",
    )

    def intent_station(request):
        return {
            **request.payload,
            "intent_captured": True,
        }

    def requirement_station(request):
        return {
            **request.payload,
            "requirements_ready": True,
        }

    def architecture_station(request):
        return {
            **request.payload,
            "architecture_ready": True,
        }

    def qa_station(request):
        return {
            **request.payload,
            "qa_passed": True,
        }

    factory.register_capability("INTENT_CAPTURE", intent_station)
    factory.register_capability("REQUIREMENT_ANALYSIS", requirement_station)
    factory.register_capability("ARCHITECTURE_DESIGN", architecture_station)
    factory.register_capability("QA_VALIDATION", qa_station)

    order = ManufacturingOrder(
        order_id="MO-E2E-001",
        product_name="AI5R Landing Page",
        product_type="WEBSITE",
        requested_by="Founder",
        requirements={
            "pages": ["home", "pricing", "contact"],
            "editable": True,
        },
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-E2E-WEB",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-E2E-WEB",
        production_line_id="LINE-E2E-WEB",
        qa_policy_id="QA-E2E-WEB",
        packaging_id="PKG-E2E-WEB",
        deployment_id="DEPLOY-E2E-WEB",
    )

    line = ProductionLine(
        line_id="LINE-E2E-WEB",
        line_name="Website Manufacturing Line",
        product_type="WEBSITE",
        station_ids=(
            "INTENT_CAPTURE",
            "REQUIREMENT_ANALYSIS",
            "ARCHITECTURE_DESIGN",
            "QA_VALIDATION",
        ),
    )

    response = factory.manufacture(
        order=order,
        recipe=recipe,
        line=line,
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["order_id"] == "MO-E2E-001"
    assert response.output["product_name"] == "AI5R Landing Page"
    assert response.output["product_type"] == "WEBSITE"
    assert response.output["intent_captured"] is True
    assert response.output["requirements_ready"] is True
    assert response.output["architecture_ready"] is True
    assert response.output["qa_passed"] is True
    assert response.metadata["factory_id"] == "DF-E2E-001"
    assert response.metadata["adapter"] == "ManufacturingRuntimeAdapter"
