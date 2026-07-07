import pytest

from OSA.CAPABILITY_RESOLVER.capability_assignment import CapabilityAssignment
from OSA.EMPLOYEE_ORCHESTRATOR.employee_orchestrator import EmployeeOrchestrator


def test_employee_orchestrator_assigns_employee_by_capability():
    assignments = [
        CapabilityAssignment(
            step="Analyze market",
            capability="MarketAnalysis",
            confidence=0.80,
        ),
        CapabilityAssignment(
            step="Create content plan",
            capability="ContentPlanning",
            confidence=0.80,
        ),
        CapabilityAssignment(
            step="Estimate budget",
            capability="FinancialPlanning",
            confidence=0.80,
        ),
    ]

    employee_assignments = EmployeeOrchestrator().assign(assignments)

    assert len(employee_assignments) == 3
    assert employee_assignments[0].employee_id == "EMP-003"
    assert employee_assignments[0].employee_role == "Research Analyst"
    assert employee_assignments[1].employee_id == "EMP-001"
    assert employee_assignments[2].employee_id == "EMP-002"


def test_employee_assignment_to_dict():
    assignments = [
        CapabilityAssignment(
            step="Evaluate result",
            capability="PerformanceEvaluation",
        )
    ]

    employee_assignment = EmployeeOrchestrator().assign(assignments)[0]
    data = employee_assignment.to_dict()

    assert data["step"] == "Evaluate result"
    assert data["capability"] == "PerformanceEvaluation"
    assert data["employee_id"] == "EMP-005"
    assert data["employee_role"] == "Performance Analyst"
    assert data["confidence"] == 0.85


def test_employee_orchestrator_rejects_empty_assignments():
    with pytest.raises(ValueError):
        EmployeeOrchestrator().assign([])
