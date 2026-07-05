import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PLANNING.planning_runtime import PlanningRuntime
from INTEGRATION.execution_pipeline import ExecutionPipeline


def test_execution_pipeline_create_from_plan():

    planning_runtime = PlanningRuntime()
    pipeline = ExecutionPipeline()

    result = planning_runtime.create(
        mission_id="MS-001",
        goal="Reduce pump downtime",
        required_capabilities=["CAP-005"],
        execution_steps=[
            {
                "step": 1,
                "action": "Inspect Pump",
                "capability_code": "CAP-005",
                "input_data": {
                    "asset_id": "PUMP-001",
                },
            },
            {
                "step": 2,
                "action": "Generate Maintenance Report",
                "capability_code": "CAP-006",
                "input_data": {
                    "asset_id": "PUMP-001",
                },
            },
        ],
    )

    plan = result["plan"]

    pipeline_result = pipeline.create_from_plan(plan)

    executions = pipeline_result["executions"]

    assert pipeline_result["status"] == "PIPELINE_CREATED"
    assert pipeline_result["plan_id"] == plan.plan_id

    assert len(executions) == 2

    assert executions[0].plan_id == plan.plan_id
    assert executions[0].step_number == 1
    assert executions[0].action == "Inspect Pump"
    assert executions[0].capability_code == "CAP-005"
    assert executions[0].input_data["asset_id"] == "PUMP-001"
    assert executions[0].metadata["mission_id"] == "MS-001"

    assert executions[1].step_number == 2
    assert executions[1].action == "Generate Maintenance Report"
    assert executions[1].capability_code == "CAP-006"

    print("EI-001 Execution Pipeline OK")


if __name__ == "__main__":
    test_execution_pipeline_create_from_plan()
