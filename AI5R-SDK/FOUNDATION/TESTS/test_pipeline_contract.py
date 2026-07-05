import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_pipeline import CanonicalPipeline, PipelineStage
from FOUNDATION.pipeline_contract import PipelineContract


def test_canonical_pipeline_implements_pipeline_contract():
    pipeline = CanonicalPipeline(
        pipeline_name="Contract Pipeline",
    )

    assert isinstance(pipeline, PipelineContract)


def test_canonical_pipeline_execute_delegates_to_run():
    pipeline = CanonicalPipeline(
        pipeline_name="Execute Pipeline",
    )

    pipeline.add_stage(PipelineStage(
        stage_id="STG-001",
        name="Add Flag",
        handler=lambda data: {
            **data,
            "executed": True,
        },
    ))

    result = pipeline.execute({"status": "ok"})

    assert result["output"]["executed"] is True
    assert len(result["history"]) == 1
