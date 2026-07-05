from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.PIPELINE import PipelineOrchestrator, PipelineStep


def test_pipeline_adds_step():
    pipeline = PipelineOrchestrator()

    pipeline.add_step(
        PipelineStep(
            name="step_1",
            runner=lambda payload: {"value": payload["value"] + 1},
        )
    )

    assert pipeline.count() == 1


def test_pipeline_requires_step_name():
    pipeline = PipelineOrchestrator()

    try:
        pipeline.add_step(
            PipelineStep(
                name="",
                runner=lambda payload: payload,
            )
        )
    except ValueError as exc:
        assert str(exc) == "Pipeline step name is required"
    else:
        raise AssertionError("Expected ValueError")


def test_pipeline_runs_steps_in_order():
    pipeline = PipelineOrchestrator()

    pipeline.add_step(
        PipelineStep(
            name="double",
            runner=lambda payload: {"value": payload["value"] * 2},
        )
    )

    pipeline.add_step(
        PipelineStep(
            name="add_three",
            runner=lambda payload: {"value": payload["value"] + 3},
        )
    )

    result = pipeline.run({"value": 5})

    assert result.status == "COMPLETED"
    assert result.steps == ["double", "add_three"]
    assert result.outputs["double"]["value"] == 10
    assert result.outputs["add_three"]["value"] == 13
