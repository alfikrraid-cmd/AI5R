import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.MULTI_AGENT_COORDINATOR import (
    CoordinationStatus,
    MultiAgentCoordinator,
)


def create_assignments():
    orchestrator = DigitalEmployeeOrchestrator()

    first = orchestrator.assign(
        task={
            "task_id": "TASK-001",
            "description": "Create campaign plan",
        },
        capability_assignment={
            "employee_id": "EMP-CONTENT",
            "capability_id": "ContentPlanning",
        },
    )

    second = orchestrator.assign(
        task={
            "task_id": "TASK-002",
            "description": "Estimate budget",
        },
        capability_assignment={
            "employee_id": "EMP-FINANCE",
            "capability_id": "FinancialPlanning",
        },
    )

    return [first, second]


def test_multi_agent_coordinator_creates_work_units():
    coordinator = MultiAgentCoordinator()

    result = coordinator.coordinate(
        goal_id="GOAL-001",
        assignments=create_assignments(),
    )

    assert result.coordination_id == "COORD-GOAL-001"
    assert result.status == CoordinationStatus.COORDINATED
    assert len(result.work_units) == 2
    assert result.work_units[0].employee_id == "EMP-CONTENT"
    assert result.work_units[1].employee_id == "EMP-FINANCE"


def test_multi_agent_coordinator_summary_contains_employees():
    coordinator = MultiAgentCoordinator()

    result = coordinator.coordinate(
        goal_id="GOAL-002",
        assignments=create_assignments(),
    )

    assert result.summary["work_unit_count"] == 2
    assert result.summary["employees"] == [
        "EMP-CONTENT",
        "EMP-FINANCE",
    ]


def test_multi_agent_coordinator_completes_work_units():
    coordinator = MultiAgentCoordinator()

    result = coordinator.coordinate(
        goal_id="GOAL-003",
        assignments=create_assignments(),
    )

    completed = coordinator.complete(
        result,
        {
            result.work_units[0].work_unit_id: {
                "output": "Campaign plan completed",
            },
            result.work_units[1].work_unit_id: {
                "output": "Budget completed",
            },
        },
    )

    assert completed.status == CoordinationStatus.COMPLETED
    assert completed.summary["completed_count"] == 2
    assert completed.work_units[0].status == CoordinationStatus.COMPLETED
    assert completed.work_units[0].result["output"] == "Campaign plan completed"


def test_multi_agent_coordinator_can_fail_coordination():
    coordinator = MultiAgentCoordinator()

    result = coordinator.coordinate(
        goal_id="GOAL-004",
        assignments=create_assignments(),
    )

    failed = coordinator.fail(result, "coordination timeout")

    assert failed.status == CoordinationStatus.FAILED
    assert failed.summary["reason"] == "coordination timeout"


def test_multi_agent_coordinator_requires_goal_id_and_assignments():
    coordinator = MultiAgentCoordinator()

    try:
        coordinator.coordinate(
            goal_id="",
            assignments=create_assignments(),
        )
    except ValueError as error:
        assert str(error) == "goal_id is required"
    else:
        raise AssertionError("ValueError was not raised")

    try:
        coordinator.coordinate(
            goal_id="GOAL-X",
            assignments=[],
        )
    except ValueError as error:
        assert str(error) == "assignments are required"
    else:
        raise AssertionError("ValueError was not raised")
