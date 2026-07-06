import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT))

from DIGITAL_WORKFLOW import (
    Workflow,
    WorkflowStep,
    WorkflowRuntime,
)


def test_workflow_runtime():

    workflow = Workflow(
        title="Marketing Campaign"
    )

    workflow.add_step(
        WorkflowStep(
            title="Research",
            assigned_role="Marketing"
        )
    )

    workflow.add_step(
        WorkflowStep(
            title="Design",
            assigned_role="Designer"
        )
    )

    assert workflow.step_count() == 2

    runtime = WorkflowRuntime()

    runtime.start(workflow)

    assert workflow.status == "RUNNING"

    runtime.finish(workflow)

    assert workflow.status == "COMPLETED"
