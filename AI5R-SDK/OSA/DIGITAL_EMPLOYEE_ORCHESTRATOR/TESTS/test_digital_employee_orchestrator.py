import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import (
    DigitalEmployeeOrchestrator,
    EmployeeAssignmentStatus,
)


def test_orchestrator_assigns_task_to_employee():
    orchestrator = DigitalEmployeeOrchestrator()

    assignment = orchestrator.assign(
        task={
            "task_id": "TASK-001",
            "goal_id": "GOAL-001",
            "description": "Create campaign plan",
        },
        capability_assignment={
            "employee_id": "EMP-001",
            "capability_id": "CAP-MARKETING",
        },
    )

    assert assignment.assignment_id == "DEA-TASK-001-EMP-001"
    assert assignment.task_id == "TASK-001"
    assert assignment.employee_id == "EMP-001"
    assert assignment.capability_id == "CAP-MARKETING"
    assert assignment.status == EmployeeAssignmentStatus.ASSIGNED


def test_orchestrator_dispatches_assignment():
    orchestrator = DigitalEmployeeOrchestrator()

    assignment = orchestrator.assign(
        task={"task_id": "TASK-002"},
        capability_assignment={
            "employee_id": "EMP-002",
            "capability_id": "CAP-WRITING",
        },
    )

    dispatched = orchestrator.dispatch(assignment.assignment_id)

    assert dispatched.status == EmployeeAssignmentStatus.DISPATCHED


def test_orchestrator_completes_assignment():
    orchestrator = DigitalEmployeeOrchestrator()

    assignment = orchestrator.assign(
        task={"task_id": "TASK-003"},
        capability_assignment={
            "employee_id": "EMP-003",
            "capability_id": "CAP-ANALYSIS",
        },
    )

    completed = orchestrator.complete(assignment.assignment_id)

    assert completed.status == EmployeeAssignmentStatus.COMPLETED


def test_orchestrator_fails_assignment():
    orchestrator = DigitalEmployeeOrchestrator()

    assignment = orchestrator.assign(
        task={"task_id": "TASK-004"},
        capability_assignment={
            "employee_id": "EMP-004",
            "capability_id": "CAP-OPS",
        },
    )

    failed = orchestrator.fail(assignment.assignment_id)

    assert failed.status == EmployeeAssignmentStatus.FAILED


def test_orchestrator_requires_task_id_employee_and_capability():
    orchestrator = DigitalEmployeeOrchestrator()

    try:
        orchestrator.assign(
            task={},
            capability_assignment={
                "employee_id": "EMP-001",
                "capability_id": "CAP-X",
            },
        )
    except ValueError as error:
        assert str(error) == "task_id is required"
    else:
        raise AssertionError("ValueError was not raised")

    try:
        orchestrator.assign(
            task={"task_id": "TASK-X"},
            capability_assignment={"capability_id": "CAP-X"},
        )
    except ValueError as error:
        assert str(error) == "employee_id is required"
    else:
        raise AssertionError("ValueError was not raised")

    try:
        orchestrator.assign(
            task={"task_id": "TASK-X"},
            capability_assignment={"employee_id": "EMP-X"},
        )
    except ValueError as error:
        assert str(error) == "capability_id is required"
    else:
        raise AssertionError("ValueError was not raised")
