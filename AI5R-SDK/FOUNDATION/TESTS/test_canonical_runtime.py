import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_identity import CanonicalIdentityGenerator
from FOUNDATION.canonical_object import CanonicalObject
from FOUNDATION.canonical_pipeline import CanonicalPipeline, PipelineStage
from FOUNDATION.canonical_runtime import CanonicalRuntime


def setup_function():
    CanonicalIdentityGenerator.reset()


def test_runtime_registers_and_runs_pipeline():
    runtime = CanonicalRuntime()

    pipeline = CanonicalPipeline(
        pipeline_name="Test Object Pipeline",
    )

    pipeline.add_stage(PipelineStage(
        stage_id="STG-001",
        name="Mark Processed",
        handler=lambda data: {
            **data,
            "processed": True,
        },
    ))

    runtime.register_pipeline(
        object_type="TEST_OBJECT",
        pipeline=pipeline,
    )

    obj = CanonicalObject(
        object_id="OBJ-001",
        object_type="TEST_OBJECT",
    )

    result = runtime.run(obj)

    assert result.input_object_id == "OBJ-001"
    assert result.input_object_type == "TEST_OBJECT"
    assert result.pipeline_id == pipeline.pipeline_id
    assert result.output["processed"] is True
    assert len(result.events) == 1


def test_runtime_emits_event():
    runtime = CanonicalRuntime()

    pipeline = CanonicalPipeline(
        pipeline_name="Event Pipeline",
    )

    runtime.register_pipeline(
        object_type="EVENT_OBJECT",
        pipeline=pipeline,
    )

    obj = CanonicalObject(
        object_id="OBJ-002",
        object_type="EVENT_OBJECT",
    )

    result = runtime.run(obj)
    event = result.events[0]

    assert event.event_type == "RUNTIME_EXECUTED"
    assert event.source_object_id == "OBJ-002"
    assert event.source_object_type == "EVENT_OBJECT"
    assert event.payload["runtime_id"] == runtime.runtime_id


def test_runtime_stores_emitted_events():
    runtime = CanonicalRuntime()

    pipeline = CanonicalPipeline(
        pipeline_name="Audit Pipeline",
    )

    runtime.register_pipeline(
        object_type="AUDIT_OBJECT",
        pipeline=pipeline,
    )

    obj = CanonicalObject(
        object_id="OBJ-003",
        object_type="AUDIT_OBJECT",
    )

    runtime.run(obj)

    assert len(runtime.emitted_events()) == 1
    assert runtime.emitted_events()[0].event_type == "RUNTIME_EXECUTED"


def test_runtime_raises_when_pipeline_missing():
    runtime = CanonicalRuntime()

    obj = CanonicalObject(
        object_id="OBJ-004",
        object_type="UNKNOWN_OBJECT",
    )

    try:
        runtime.run(obj)
        assert False
    except KeyError as error:
        assert "PIPELINE:UNKNOWN_OBJECT" in str(error)
