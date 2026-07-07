import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.MULTI_AGENT_COORDINATOR import MultiAgentCoordinator
from OSA.ORGANIZATION_RUNTIME import OrganizationRuntime, OrganizationRuntimeStatus
from OSA.STUDIO_LIVE_OPS import StudioLiveOps


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


def test_studio_live_ops_builds_empty_live_snapshot():
    snapshot = StudioLiveOps().build_snapshot()

    assert snapshot.status == "LIVE"
    assert snapshot.goals == []
    assert snapshot.employees == []
    assert snapshot.runtimes == []
    assert snapshot.tools == []
    assert snapshot.memory == []
    assert snapshot.events == []


def test_studio_live_ops_builds_snapshot_from_runtime_result():
    runtime_result = create_runtime_result()

    snapshot = StudioLiveOps().build_from_runtime_result(runtime_result)

    assert snapshot.status == "LIVE"
    assert snapshot.goals[0]["goal_id"] == "GOAL-001"
    assert snapshot.goals[0]["status"] == OrganizationRuntimeStatus.ACTIVE.value
    assert snapshot.runtimes[0]["runtime_id"] == "ORG-RUN-GOAL-001"
    assert snapshot.runtimes[0]["work_unit_count"] == 2
    assert snapshot.events[0]["event_type"] == "STUDIO_RUNTIME_SNAPSHOT"


def test_studio_live_ops_requires_runtime_result():
    try:
        StudioLiveOps().build_from_runtime_result(None)
    except ValueError as error:
        assert str(error) == "runtime_result is required"
    else:
        raise AssertionError("ValueError was not raised")
