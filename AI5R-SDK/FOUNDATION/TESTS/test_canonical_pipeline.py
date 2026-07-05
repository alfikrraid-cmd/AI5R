import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_identity import CanonicalIdentityGenerator
from FOUNDATION.canonical_pipeline import CanonicalPipeline, PipelineStage


def setup_function():
    CanonicalIdentityGenerator.reset()


def test_pipeline_auto_generates_identity():
    pipeline = CanonicalPipeline(
        pipeline_name="Knowledge Pipeline",
    )

    assert pipeline.pipeline_id.startswith("AI5R-PIPE-")
    assert CanonicalIdentityGenerator.current_counter("PIPE") == 1


def test_pipeline_adds_stage():
    pipeline = CanonicalPipeline(
        pipeline_name="Knowledge Pipeline",
    )

    pipeline.add_stage(PipelineStage(
        stage_id="STG-001",
        name="Extract",
    ))

    assert len(pipeline.stages) == 1
    assert pipeline.stages[0].name == "Extract"


def test_pipeline_runs_stages():
    pipeline = CanonicalPipeline(
        pipeline_name="Number Pipeline",
    )

    pipeline.add_stage(PipelineStage(
        stage_id="STG-001",
        name="Add One",
        handler=lambda value: value + 1,
    ))

    pipeline.add_stage(PipelineStage(
        stage_id="STG-002",
        name="Double",
        handler=lambda value: value * 2,
    ))

    result = pipeline.run(3)

    assert result["input"] == 3
    assert result["output"] == 8
    assert len(result["history"]) == 2
    assert result["history"][0]["output"] == 4


def test_pipeline_serializes_without_callable():
    pipeline = CanonicalPipeline(
        pipeline_name="Serializable Pipeline",
    )

    pipeline.add_stage(PipelineStage(
        stage_id="STG-001",
        name="Extract",
        handler=lambda value: value,
    ))

    data = pipeline.serialize()

    assert data["pipeline_name"] == "Serializable Pipeline"
    assert data["stages"][0]["has_handler"] is True
    assert "handler" not in data["stages"][0]


def test_pipeline_creates_completion_event():
    pipeline = CanonicalPipeline(
        pipeline_name="Event Pipeline",
        metadata={"layer": "foundation"},
    )

    result = pipeline.run({"status": "ok"})
    event = pipeline.to_event(
        event_id="EV-PIPE-001",
        result=result,
    )

    assert event.event_type == "PIPELINE_COMPLETED"
    assert event.source_object_id == pipeline.pipeline_id
    assert event.source_object_type == "PIPELINE"
    assert event.payload["output"]["status"] == "ok"
