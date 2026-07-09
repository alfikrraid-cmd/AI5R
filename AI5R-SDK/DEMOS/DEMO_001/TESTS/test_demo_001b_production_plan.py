from DEMOS.DEMO_001.login_api_demo import run_demo
from DEMOS.DEMO_001.production_plan import Demo001ProductionPlan


def test_demo_001b_creates_production_plan_from_order():
    demo = run_demo()
    order = demo["order"]

    plan = Demo001ProductionPlan().create_from_order(order)

    assert plan["status"] == "PRODUCTION_PLAN_CREATED"
    assert plan["order_id"] == order.order_id
    assert plan["product_type"] == "FASTAPI_SERVICE"
    assert "app/main.py" in plan["artifacts"]
    assert "app/routers/auth.py" in plan["artifacts"]
    assert "tests/test_login.py" in plan["artifacts"]
    assert "requirements.txt" in plan["artifacts"]
    assert "README.md" in plan["artifacts"]
    assert plan["metadata"]["blueprint"] == "FASTAPI_LOGIN_API_BLUEPRINT"


def test_demo_001b_rejects_wrong_product_type():
    demo = run_demo()
    order = demo["order"]
    object.__setattr__(order, "product_type", "LANDING_PAGE")

    try:
        Demo001ProductionPlan().create_from_order(order)
    except ValueError as exc:
        assert "Unsupported product_type" in str(exc)
    else:
        raise AssertionError("Expected unsupported product type to fail")
