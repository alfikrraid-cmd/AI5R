from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from RUNTIME import (
    ManufacturingRuntimeAdapter,
    RuntimeEngine,
    RuntimeStatus,
)


def test_manufacturing_adapter_executes_order_through_runtime_pipeline():
    engine = RuntimeEngine()

    def requirements_station(request):
        return {
            **request.payload,
            "requirements_captured": True,
        }

    def architecture_station(request):
        return {
            **request.payload,
            "architecture_created": True,
        }

    engine.register_handler("manufacturing", "REQ-STATION", requirements_station)
    engine.register_handler("manufacturing", "ARCH-STATION", architecture_station)

    adapter = ManufacturingRuntimeAdapter(engine=engine)

    order = ManufacturingOrder(
        order_id="MO-001",
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
            "REQ-STATION",
            "ARCH-STATION",
        ),
    )

    response = adapter.execute_order(
        order=order,
        recipe=recipe,
        line=line,
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["order_id"] == "MO-001"
    assert response.output["product_name"] == "AI5R Website"
    assert response.output["requirements_captured"] is True
    assert response.output["architecture_created"] is True
    assert response.metadata["adapter"] == "ManufacturingRuntimeAdapter"


def test_manufacturing_adapter_rejects_invalid_order():
    engine = RuntimeEngine()
    adapter = ManufacturingRuntimeAdapter(engine=engine)

    order = ManufacturingOrder(
        order_id="",
        product_name="",
        product_type="",
        requested_by="",
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
        station_ids=("REQ-STATION",),
    )

    try:
        adapter.execute_order(order, recipe, line)
    except ValueError as exc:
        assert str(exc) == "manufacturing order is invalid"
    else:
        raise AssertionError("Expected ValueError")


def test_manufacturing_adapter_rejects_product_type_mismatch():
    engine = RuntimeEngine()
    adapter = ManufacturingRuntimeAdapter(engine=engine)

    order = ManufacturingOrder(
        order_id="MO-002",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Founder",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-ERP",
        recipe_name="ERP Recipe",
        product_type="ERP",
        dbom_id="DBOM-ERP",
        production_line_id="LINE-ERP",
        qa_policy_id="QA-ERP",
        packaging_id="PKG-ERP",
        deployment_id="DEPLOY-ERP",
    )

    line = ProductionLine(
        line_id="LINE-ERP",
        line_name="ERP Production Line",
        product_type="ERP",
        station_ids=("REQ-STATION",),
    )

    try:
        adapter.execute_order(order, recipe, line)
    except ValueError as exc:
        assert str(exc) == "order and recipe product type mismatch"
    else:
        raise AssertionError("Expected ValueError")


def test_manufacturing_adapter_rejects_recipe_line_mismatch():
    engine = RuntimeEngine()
    adapter = ManufacturingRuntimeAdapter(engine=engine)

    order = ManufacturingOrder(
        order_id="MO-003",
        product_name="AI Agent",
        product_type="AI_AGENT",
        requested_by="Founder",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-AI",
        recipe_name="AI Agent Recipe",
        product_type="AI_AGENT",
        dbom_id="DBOM-AI",
        production_line_id="LINE-AI",
        qa_policy_id="QA-AI",
        packaging_id="PKG-AI",
        deployment_id="DEPLOY-AI",
    )

    line = ProductionLine(
        line_id="LINE-WRONG",
        line_name="Wrong Line",
        product_type="AI_AGENT",
        station_ids=("REQ-STATION",),
    )

    try:
        adapter.execute_order(order, recipe, line)
    except ValueError as exc:
        assert str(exc) == "recipe and production line mismatch"
    else:
        raise AssertionError("Expected ValueError")
