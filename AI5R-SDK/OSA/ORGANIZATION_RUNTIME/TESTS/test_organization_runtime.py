import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.MULTI_AGENT_COORDINATOR import MultiAgentCoordinator
from OSA.ORGANIZATION_RUNTIME import (
    OrganizationRuntime,
    OrganizationRuntimeStatus,
)


def create_coordination_result():
    orchestrator = DigitalEmployeeOrchestrator()

    assignments = [
        orchestrator.assign(
            task={"task_id": "TASK-001"},
            capability_assignment={
                "employee_id": "EMP-CONTENT",
                "capability_id": "ContentPlanning",
            },
        ),
        orchestrator.assign(
            task={"task_id": "TASK-002"},
            capability_assignment={
                "employee_id": "EMP-FINANCE",
                "capability_id": "FinancialPlanning",
            },
        ),
    ]

    return MultiAgentCoordinator().coordinate(
        goal_id="GOAL-001",
        assignments=assignments,
    )


def test_organization_runtime_starts_from_coordination():
    coordination = create_coordination_result()

    result = OrganizationRuntime().start(
        goal_id="GOAL-001",
        coordination_result=coordination,
    )

    assert result.runtime_id == "ORG-RUN-GOAL-001"
    assert result.goal_id == "GOAL-001"
    assert result.status == OrganizationRuntimeStatus.ACTIVE
    assert result.coordination_id == coordination.coordination_id
    assert result.work_unit_count == 2


def test_organization_runtime_completes():
    coordination = create_coordination_result()
    runtime = OrganizationRuntime()

    result = runtime.start("GOAL-001", coordination)
    completed = runtime.complete(result)

    assert completed.status == OrganizationRuntimeStatus.COMPLETED
    assert completed.summary["completed"] is True


def test_organization_runtime_fails():
    coordination = create_coordination_result()
    runtime = OrganizationRuntime()

    result = runtime.start("GOAL-001", coordination)
    failed = runtime.fail(result, "organization timeout")

    assert failed.status == OrganizationRuntimeStatus.FAILED
    assert failed.summary["reason"] == "organization timeout"


def test_organization_runtime_requires_goal_id_and_coordination_result():
    runtime = OrganizationRuntime()

    try:
        runtime.start("", create_coordination_result())
    except ValueError as error:
        assert str(error) == "goal_id is required"
    else:
        raise AssertionError("ValueError was not raised")

    try:
        runtime.start("GOAL-X", None)
    except ValueError as error:
        assert str(error) == "coordination_result is required"
    else:
        raise AssertionError("ValueError was not raised")
