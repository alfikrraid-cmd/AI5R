from SALES import SalesExecutiveRuntime, SalesTarget


def test_sales_executive_creates_sales_plan():
    runtime = SalesExecutiveRuntime()

    target = SalesTarget(
        revenue_target=300_000_000,
        period="monthly",
        currency="IDR",
    )

    plan = runtime.create_sales_plan(
        target=target,
        average_deal_size=30_000_000,
        conversion_rate=0.2,
    )

    assert plan.required_closings == 10
    assert plan.required_leads == 50
    assert plan.conversion_rate == 0.2
    assert "Generate qualified leads" in plan.actions


def test_sales_executive_rejects_invalid_target():
    runtime = SalesExecutiveRuntime()

    target = SalesTarget(revenue_target=0)

    try:
        runtime.create_sales_plan(
            target=target,
            average_deal_size=30_000_000,
            conversion_rate=0.2,
        )
    except ValueError as exc:
        assert "Revenue target" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
