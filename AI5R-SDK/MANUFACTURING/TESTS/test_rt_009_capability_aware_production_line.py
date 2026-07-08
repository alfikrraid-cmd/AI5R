from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory
from RUNTIME import RuntimeStatus


def test_production_line_supports_capability_ids():
    line = ProductionLine(
        line_id="LINE-CAP-001",
        line_name="Capability Based Line",
        product_type="WEBSITE",
        capability_ids=(
            "REQUIREMENT_ANALYSIS",
            "ARCHITECTURE_DESIGN",
        ),
    )

    assert line.validate() is True
    assert line.is_capability_based() is True
    assert line.capability_count() == 2
    assert line.execution_ids() == (
        "REQUIREMENT_ANALYSIS",
        "ARCHITECTURE_DESIGN",
    )


def test_production_line_keeps_station_ids_as_legacy_path():
    line = ProductionLine(
        line_id="LINE-LEGACY-001",
        line_name="Legacy Station Line",
        product_type="WEBSITE",
        station_ids=(
            "REQ-STATION",
            "ARCH-STATION",
        ),
    )

    assert line.validate() is True
    assert line.is_capability_based() is False
    assert line.station_count() == 2
    assert line.execution_ids() == (
        "REQ-STATION",
        "ARCH-STATION",
    )


def test_capability_ids_take_priority_over_station_ids():
    line = ProductionLine(
        line_id="LINE-MIXED-001",
        line_name="Mixed Line",
        product_type="WEBSITE",
        station_ids=("LEGACY-STATION",),
        capability_ids=("REQUIREMENT_ANALYSIS",),
    )

    assert line.execution_ids() == ("REQUIREMENT_ANALYSIS",)
    assert line.execution_count() == 1


def test_digital_factory_manufactures_with_capability_based_line():
    factory = DigitalFactory(
        factory_id="DF-CAP-001",
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
        order_id="MO-CAP-001",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Founder",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-CAP-WEB",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-CAP-WEB",
        production_line_id="LINE-CAP-WEB",
        qa_policy_id="QA-CAP-WEB",
        packaging_id="PKG-CAP-WEB",
        deployment_id="DEPLOY-CAP-WEB",
    )

    line = ProductionLine(
        line_id="LINE-CAP-WEB",
        line_name="Website Capability Line",
        product_type="WEBSITE",
        capability_ids=(
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
    assert response.output["requirements_analyzed"] is True
    assert response.output["architecture_designed"] is True
    assert response.metadata["line_is_capability_based"] is True
