from pathlib import Path

from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING_CENTER import ManufacturingOrchestrator
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus


def make_factory() -> DigitalFactory:
    factory = DigitalFactory(
        factory_id="DF-DYNAMIC-001",
        factory_name="AI5R Dynamic Factory",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-DYNAMIC-001",
        recipe_name="Dynamic Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-DYNAMIC-001",
        production_line_id="LINE-DYNAMIC-001",
        qa_policy_id="QA-DYNAMIC-001",
        packaging_id="PKG-DYNAMIC-001",
        deployment_id="DEPLOY-DYNAMIC-001",
    )

    line = ProductionLine(
        line_id="LINE-DYNAMIC-001",
        line_name="Dynamic Website Line",
        product_type="WEBSITE",
        capability_ids=(
            "REQUIREMENT_ANALYSIS",
            "ARCHITECTURE_DESIGN",
            "PACKAGE_ARTIFACT",
        ),
    )

    factory.register_recipe(recipe, line)

    def requirement_analysis(request):
        return {
            **request.payload,
            "requirements_ready": True,
        }

    def architecture_design(request):
        return {
            **request.payload,
            "architecture_ready": True,
        }

    def package_artifact(request):
        return {
            **request.payload,
            "packaged": True,
            "artifacts": ["build/dynamic-site.zip"],
        }

    factory.register_capability(
        "REQUIREMENT_ANALYSIS",
        requirement_analysis,
    )
    factory.register_capability(
        "ARCHITECTURE_DESIGN",
        architecture_design,
    )
    factory.register_capability(
        "PACKAGE_ARTIFACT",
        package_artifact,
    )

    return factory


def test_executes_all_capabilities_in_order(tmp_path: Path) -> None:
    orchestrator = ManufacturingOrchestrator(
        factory=make_factory(),
        workspace=tmp_path,
    )

    order = ManufacturingOrder(
        order_id="MO-DYNAMIC-001",
        product_name="Dynamic Website",
        product_type="WEBSITE",
        requested_by="Chief",
    )

    result = orchestrator.manufacture(order=order)

    assert result.status is ManufacturingStatus.COMPLETED
    assert result.metadata["runtime_output"]["requirements_ready"] is True
    assert result.metadata["runtime_output"]["architecture_ready"] is True
    assert result.metadata["runtime_output"]["packaged"] is True
    assert result.artifacts == ["build/dynamic-site.zip"]
    assert result.metadata["runtime_definition"] == "PACKAGE_ARTIFACT"


def test_stops_on_failed_capability(tmp_path: Path) -> None:
    factory = make_factory()

    def broken_architecture(request):
        raise RuntimeError("architecture failed")

    factory.register_capability(
        "ARCHITECTURE_DESIGN",
        broken_architecture,
    )

    orchestrator = ManufacturingOrchestrator(
        factory=factory,
        workspace=tmp_path,
    )

    order = ManufacturingOrder(
        order_id="MO-DYNAMIC-002",
        product_name="Broken Website",
        product_type="WEBSITE",
        requested_by="Chief",
    )

    result = orchestrator.manufacture(order=order)

    assert result.status is ManufacturingStatus.FAILED
    assert result.logs == [
        "Manufacturing failed: architecture failed"
    ]
