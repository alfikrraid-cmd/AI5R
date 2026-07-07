import pytest

from OSA.CAPABILITY_RESOLVER.capability_resolver import CapabilityResolver
from OSA.PLANNER.plan_object import PlanObject


def test_capability_resolver_assigns_capabilities():
    plan = PlanObject(
        task_id="TASK-001",
        goal="Create marketing strategy",
        steps=[
            "Analyze market",
            "Define target customer",
            "Create content plan",
            "Estimate budget",
            "Evaluate result",
        ],
    )

    assignments = CapabilityResolver().resolve(plan)

    assert len(assignments) == 5
    assert assignments[0].capability == "MarketAnalysis"
    assert assignments[2].capability == "ContentPlanning"
    assert assignments[3].capability == "FinancialPlanning"
    assert assignments[4].capability == "PerformanceEvaluation"


def test_capability_assignment_to_dict():
    plan = PlanObject(
        task_id="TASK-001",
        goal="Create marketing strategy",
        steps=["Analyze market"],
    )

    assignment = CapabilityResolver().resolve(plan)[0]
    data = assignment.to_dict()

    assert data["step"] == "Analyze market"
    assert data["capability"] == "MarketAnalysis"
    assert data["confidence"] == 0.80


def test_capability_resolver_rejects_empty_steps():
    plan = PlanObject(
        task_id="TASK-001",
        goal="Empty plan",
        steps=[],
    )

    with pytest.raises(ValueError):
        CapabilityResolver().resolve(plan)
