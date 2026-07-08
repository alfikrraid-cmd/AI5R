from pathlib import Path

from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory
from RUNTIME import RuntimeStatus


def test_digital_factory_manufactures_website_artifact():
    output_dir = Path("AI5R-SDK/PRODUCTS/SMOKE-WEBSITE")
    output_file = output_dir / "index.html"

    if output_file.exists():
        output_file.unlink()

    factory = DigitalFactory(
        factory_id="DF-SF-001",
        factory_name="AI5R Digital Factory",
    )

    def website_artifact_generation(request):
        output_dir.mkdir(parents=True, exist_ok=True)

        html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>AI5R Smoke Website</title>
</head>
<body>
  <h1>AI5R Digital Factory</h1>
  <p>This website artifact was manufactured by AI5R.</p>
</body>
</html>
"""
        output_file.write_text(html)

        return {
            **request.payload,
            "artifact_created": True,
            "artifact_path": str(output_file),
        }

    factory.register_capability(
        "WEBSITE_ARTIFACT_GENERATION",
        website_artifact_generation,
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-SMOKE-WEB",
        recipe_name="Smoke Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-SMOKE-WEB",
        production_line_id="LINE-SMOKE-WEB",
        qa_policy_id="QA-SMOKE-WEB",
        packaging_id="PKG-SMOKE-WEB",
        deployment_id="DEPLOY-SMOKE-WEB",
    )

    line = ProductionLine(
        line_id="LINE-SMOKE-WEB",
        line_name="Smoke Website Line",
        product_type="WEBSITE",
        capability_ids=("WEBSITE_ARTIFACT_GENERATION",),
    )

    factory.register_recipe(recipe, line)

    order = ManufacturingOrder(
        order_id="MO-SF-001",
        product_name="AI5R Smoke Website",
        product_type="WEBSITE",
        requested_by="Founder",
    )

    response = factory.manufacture_order(order)

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["artifact_created"] is True
    assert output_file.exists()
    assert "AI5R Digital Factory" in output_file.read_text()
