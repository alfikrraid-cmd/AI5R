import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.MULTI_AGENT_COORDINATOR import MultiAgentCoordinator
from OSA.ORGANIZATION_RUNTIME import OrganizationRuntime, OrganizationRuntimeStatus
from OSA.RUNTIME_DASHBOARD_INTEGRATION import RuntimeDashboardIntegration


def create_runtime_result():
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

    coordination = MultiAgentCoordinator().coordinate(
        goal_id="GOAL-001",
        assignments=assignments,
    )

    return OrganizationRuntime().start(
        goal_id="GOAL-001",
        coordination_result=coordination,
    )


def test_runtime_dashboard_integration_publishes_started_event():
    runtime_result = create_runtime_result()

    event = RuntimeDashboardIntegration().publish_runtime_started(runtime_result)

    assert event.event_type == "RUNTIME_STARTED"
    assert event.runtime_id == "ORG-RUN-GOAL-001"
    assert event.goal_id == "GOAL-001"
    assert event.status == OrganizationRuntimeStatus.ACTIVE.value
    assert event.payload["work_unit_count"] == 2


def test_runtime_dashboard_integration_publishes_completed_event():
    runtime = OrganizationRuntime()
    runtime_result = create_runtime_result()
    completed = runtime.complete(runtime_result)

    event = RuntimeDashboardIntegration().publish_runtime_completed(completed)

    assert event.event_type == "RUNTIME_COMPLETED"
    assert event.status == OrganizationRuntimeStatus.COMPLETED.value
    assert event.payload["summary"]["completed"] is True


def test_runtime_dashboard_integration_publishes_failed_event():
    runtime = OrganizationRuntime()
    runtime_result = create_runtime_result()
    failed = runtime.fail(runtime_result, "dashboard integration timeout")

    event = RuntimeDashboardIntegration().publish_runtime_failed(failed)

    assert event.event_type == "RUNTIME_FAILED"
    assert event.status == OrganizationRuntimeStatus.FAILED.value
    assert event.payload["summary"]["reason"] == "dashboard integration timeout"


def test_runtime_dashboard_integration_requires_runtime_result():
    try:
        RuntimeDashboardIntegration().publish_runtime_started(None)
    except ValueError as error:
        assert str(error) == "runtime_result is required"
    else:
        raise AssertionError("ValueError was not raised")
