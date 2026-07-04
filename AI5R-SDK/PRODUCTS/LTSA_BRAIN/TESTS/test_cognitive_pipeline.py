import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "AI5R-SDK"))

from PRODUCTS.LTSA_BRAIN.cognitive_pipeline import EnterpriseCognitivePipeline


def test_pipeline_creates_full_cognitive_chain():
    pipeline = EnterpriseCognitivePipeline()

    result = pipeline.process(
        {
            "pump_id": "P-001",
            "finding": "high vibration",
        }
    )

    objects = result["objects"]

    assert len(objects) == 9
    assert objects[0].object_type == "reality_object"
    assert objects[-1].object_type == "learning_object"


def test_pipeline_preserves_single_trace_id():
    pipeline = EnterpriseCognitivePipeline()
    result = pipeline.process({"finding": "seal leak"})

    trace_ids = {obj.trace_id for obj in result["objects"]}

    assert len(trace_ids) == 1
    assert result["trace_id"] in trace_ids


def test_pipeline_links_parent_child_chain():
    pipeline = EnterpriseCognitivePipeline()
    result = pipeline.process({"finding": "bearing noise"})

    objects = result["objects"]

    for index in range(1, len(objects)):
        parent = objects[index - 1]
        child = objects[index]

        assert child.parent_id == parent.id
        assert child.id in parent.children


def test_pipeline_latest_is_learning_object():
    pipeline = EnterpriseCognitivePipeline()
    result = pipeline.process({"finding": "temperature rise"})

    latest = result["latest"]

    assert latest.object_type == "learning_object"
    assert latest.payload["learning"]["status"] == "pending"


def test_pipeline_history_matches_objects():
    pipeline = EnterpriseCognitivePipeline()
    result = pipeline.process({"finding": "low flow"})

    assert pipeline.history == result["objects"]
