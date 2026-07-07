import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.RUNTIME_PIPELINE import RuntimePipeline


def test_runtime_pipeline_runs_goal_to_memory():
    pipeline = RuntimePipeline()

    result = pipeline.run(
        {
            "goal_id": "GOAL-001",
            "description": "Create marketing campaign",
            "desired_outcomes": [
                "Create campaign plan",
                "Create content calendar",
            ],
        }
    )

    assert result.pipeline_id == "PIPE-GOAL-001"
    assert result.goal_id == "GOAL-001"
    assert result.task_count == 2
    assert result.execution_count == result.task_count
    assert result.memory_count == result.task_count
    assert len(result.memories) == result.task_count
    assert result.memories[0].status.value == "LEARNED"


def test_runtime_pipeline_uses_description_when_no_desired_outcomes():
    pipeline = RuntimePipeline()

    result = pipeline.run(
        {
            "goal_id": "GOAL-002",
            "description": "Evaluate campaign result",
        }
    )

    assert result.pipeline_id == "PIPE-GOAL-002"
    assert result.task_count == 1
    assert result.memory_count == 1


def test_runtime_pipeline_requires_goal_id():
    pipeline = RuntimePipeline()

    try:
        pipeline.run(
            {
                "description": "Create marketing campaign",
                "desired_outcomes": ["Create campaign plan"],
            }
        )
    except ValueError as error:
        assert str(error) == "goal_id is required"
    else:
        raise AssertionError("ValueError was not raised")


def test_runtime_pipeline_requires_goal_content():
    pipeline = RuntimePipeline()

    try:
        pipeline.run({"goal_id": "GOAL-003"})
    except ValueError as error:
        assert str(error) == "goal description or desired_outcomes is required"
    else:
        raise AssertionError("ValueError was not raised")


def test_runtime_pipeline_execute_accepts_command_string():
    pipeline = RuntimePipeline()

    result = pipeline.execute(
        command="Create UMKM marketing campaign",
        employee_id="EMP-001",
    )

    assert result.pipeline_id.startswith("PIPE-CMD-")
    assert result.goal_id.startswith("CMD-")
    assert result.task_count == 1
    assert result.execution_count == 1
    assert result.memory_count == 1
