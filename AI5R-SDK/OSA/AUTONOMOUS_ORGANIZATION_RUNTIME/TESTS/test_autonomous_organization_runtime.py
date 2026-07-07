import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.AUTONOMOUS_ORGANIZATION_RUNTIME import AutonomousOrganizationRuntime
from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.MULTI_AGENT_COORDINATOR import MultiAgentCoordinator
from OSA.ORGANIZATION_RUNTIME import OrganizationRuntime, OrganizationRuntimeStatus


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


def test_autonomous_organization_runtime_completes():
    runtime = AutonomousOrganizationRuntime(
        organization_runtime=OrganizationRuntime(),
    )

    result = runtime.run(
        goal_id="GOAL-001",
        coordination_result=create_coordination_result(),
    )

    assert result.goal_id == "GOAL-001"
    assert result.status == "COMPLETED"
    assert result.runtime_result.status == OrganizationRuntimeStatus.COMPLETED
    assert result.llm_response.provider == "MOCK"
    assert result.dashboard_events[0].event_type == "RUNTIME_STARTED"
    assert result.dashboard_events[1].event_type == "RUNTIME_COMPLETED"


def test_autonomous_organization_runtime_requires_goal_id():
    runtime = AutonomousOrganizationRuntime(
        organization_runtime=OrganizationRuntime(),
    )

    try:
        runtime.run("", create_coordination_result())
    except ValueError as error:
        assert str(error) == "goal_id is required"
    else:
        raise AssertionError("ValueError was not raised")


def test_autonomous_organization_runtime_requires_coordination_result():
    runtime = AutonomousOrganizationRuntime(
        organization_runtime=OrganizationRuntime(),
    )

    try:
        runtime.run("GOAL-001", None)
    except ValueError as error:
        assert str(error) == "coordination_result is required"
    else:
        raise AssertionError("ValueError was not raised")
