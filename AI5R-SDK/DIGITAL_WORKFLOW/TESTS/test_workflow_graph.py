import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_WORKFLOW import Workflow, WorkflowStep, WorkflowGraph


def test_workflow_dependency_graph():

    workflow = Workflow(title="Launch Campaign")

    research = WorkflowStep(
        title="Research",
        assigned_role="Marketing"
    )

    design = WorkflowStep(
        title="Design",
        assigned_role="Designer",
        depends_on=[research.step_id]
    )

    workflow.add_step(research)
    workflow.add_step(design)

    graph = WorkflowGraph()

    ready = graph.ready_steps(workflow)

    assert len(ready) == 1
    assert ready[0].title == "Research"

    graph.complete_step(research)

    ready = graph.ready_steps(workflow)

    assert len(ready) == 1
    assert ready[0].title == "Design"
