from SALES import ExecutiveGoal, SalesExecutiveOrchestrator
from SALES.REPORTING import ExecutiveReport


def test_sales_executive_orchestrator_end_to_end():
    executive = SalesExecutiveOrchestrator()

    executive.receive_goal(
        ExecutiveGoal(
            goal_id="GOAL-001",
            description="Reach monthly revenue target",
            target_value=300_000_000,
            period="monthly",
            currency="IDR",
        )
    )

    analysis = executive.analyze()

    assert analysis["target_value"] == 300_000_000

    plan = executive.create_plan(
        average_deal_size=30_000_000,
        conversion_rate=0.2,
    )

    assert plan.required_closings == 10
    assert plan.required_leads == 50

    result = executive.execute(
        customer_id="CUST-001",
        customer_name="PT Astra",
        opportunity_id="OPP-001",
        opportunity_value=50_000_000,
    )

    assert result["customer"].name == "PT Astra"
    assert result["proposal"].proposal_id == "PROP-OPP-001"
    assert result["quotation"].grand_total == 55_500_000
    assert result["contract"].value == 55_500_000

    report = executive.report()

    assert isinstance(report, ExecutiveReport)
    assert report.executive == "Sales Executive"
    assert report.kpis["required_leads"] == 50
    assert report.kpis["pipeline_open_value"] == 50_000_000
    assert "Review pipeline weekly." in report.next_actions


def test_sales_executive_requires_goal_before_analysis():
    executive = SalesExecutiveOrchestrator()

    try:
        executive.analyze()
    except ValueError as exc:
        assert "Goal is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_sales_executive_rejects_invalid_goal():
    executive = SalesExecutiveOrchestrator()

    try:
        executive.receive_goal(
            ExecutiveGoal(
                goal_id="GOAL-001",
                description="Invalid goal",
                target_value=0,
            )
        )
    except ValueError as exc:
        assert "Goal target value" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
