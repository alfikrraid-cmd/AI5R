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
    assert result.task_count >= 1
    assert result.execution_count == result.task_count
    assert result.memory_count == result.task_count
    assert len(result.memories) == result.task_count


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
