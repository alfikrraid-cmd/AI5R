from pathlib import Path
from threading import Barrier

from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING_CENTER.manufacturing_orchestrator import (
    ManufacturingOrchestrator,
)
from MANUFACTURING_CENTER.manufacturing_status import (
    ManufacturingStatus,
)


def test_orchestrator_executes_independent_capabilities_in_parallel(
    tmp_path: Path,
) -> None:
    factory = DigitalFactory(
        factory_id="DF-PARALLEL-001",
        factory_name="AI5R Parallel Factory",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-PARALLEL-001",
        recipe_name="Parallel Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-PARALLEL-001",
        production_line_id="LINE-PARALLEL-001",
        qa_policy_id="QA-PARALLEL-001",
        packaging_id="PKG-PARALLEL-001",
        deployment_id="DEPLOY-PARALLEL-001",
    )

    line = ProductionLine(
        line_id="LINE-PARALLEL-001",
        line_name="Parallel Website Line",
        product_type="WEBSITE",
        capability_ids=(
            "REQUIREMENTS",
            "FRONTEND",
            "BACKEND",
            "INTEGRATION",
        ),
        metadata={
            "dependencies": {
                "FRONTEND": ["REQUIREMENTS"],
                "BACKEND": ["REQUIREMENTS"],
                "INTEGRATION": [
                    "FRONTEND",
                    "BACKEND",
                ],
            },
        },
    )

    factory.register_recipe(recipe, line)

    parallel_barrier = Barrier(2, timeout=2)

    def requirements(request):
        return {
            **request.payload,
            "requirements_ready": True,
        }

    def frontend(request):
        parallel_barrier.wait()

        return {
            **request.payload,
            "frontend_ready": True,
            "artifacts": ["build/frontend.zip"],
        }

    def backend(request):
        parallel_barrier.wait()

        return {
            **request.payload,
            "backend_ready": True,
            "artifacts": ["build/backend.zip"],
        }

    def integration(request):
        assert request.payload["frontend_ready"] is True
        assert request.payload["backend_ready"] is True

        return {
            **request.payload,
            "integration_ready": True,
        }

    factory.register_capability(
        "REQUIREMENTS",
        requirements,
    )
    factory.register_capability(
        "FRONTEND",
        frontend,
    )
    factory.register_capability(
        "BACKEND",
        backend,
    )
    factory.register_capability(
        "INTEGRATION",
        integration,
    )

    orchestrator = ManufacturingOrchestrator(
        factory=factory,
        workspace=tmp_path,
    )

    order = ManufacturingOrder(
        order_id="MO-PARALLEL-001",
        product_name="Parallel Website",
        product_type="WEBSITE",
        requested_by="Chief",
    )

    result = orchestrator.manufacture(order=order)

    assert result.status is ManufacturingStatus.COMPLETED

    output = result.metadata["runtime_output"]

    assert output["requirements_ready"] is True
    assert output["frontend_ready"] is True
    assert output["backend_ready"] is True
    assert output["integration_ready"] is True

    assert result.artifacts == [
        "build/backend.zip",
        "build/frontend.zip",
    ]

    assert result.metadata["execution_levels"] == [
        ["REQUIREMENTS"],
        ["BACKEND", "FRONTEND"],
        ["INTEGRATION"],
    ]

    assert result.metadata["max_parallelism"] == 2
