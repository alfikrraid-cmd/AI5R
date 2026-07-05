from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.PIPELINE.ltsa_ai_pipeline import build_ltsa_ai_pipeline


def test_ltsa_ai_pipeline_runs_end_to_end():
    pipeline = build_ltsa_ai_pipeline()

    result = pipeline.run(
        {
            "source": "manual_input",
            "payload": {
                "observation": "customer needs technical service agreement support"
            },
            "metadata": {
                "product": "LTSA-AI"
            },
            "context": {
                "customer_type": "enterprise"
            },
        }
    )

    assert result.status == "COMPLETED"
    assert result.steps == [
        "reality",
        "warehouse",
        "experience",
        "memory",
        "knowledge",
        "capability",
        "context",
        "reasoning",
        "decision",
        "recommendation",
        "action",
    ]

    assert result.outputs["reality"]["type"] == "REALITY_OBJECT"
    assert result.outputs["warehouse"]["type"] == "WAREHOUSE_OBJECT"
    assert result.outputs["experience"]["type"] == "EXPERIENCE_OBJECT"
    assert result.outputs["memory"]["type"] == "MEMORY_OBJECT"
    assert result.outputs["knowledge"]["type"] == "KNOWLEDGE_OBJECT"
    assert result.outputs["capability"]["type"] == "CAPABILITY_OBJECT"
    assert result.outputs["context"]["type"] == "CONTEXT_OBJECT"
    assert result.outputs["reasoning"]["type"] == "REASONING_OBJECT"
    assert result.outputs["decision"]["type"] == "DECISION_OBJECT"
    assert result.outputs["recommendation"]["type"] == "RECOMMENDATION_OBJECT"
    assert result.outputs["action"]["type"] == "ACTION_OBJECT"
    assert result.outputs["action"]["action_data"]["action"] == "execute_next_step"
