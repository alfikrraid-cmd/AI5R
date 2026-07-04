import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.enterprise_cognitive_pipeline import EnterpriseCognitivePipeline


def test_enterprise_cognitive_pipeline_runs_end_to_end():

    reality = {
        "object_id": "reality-015",
        "object_type": "reality",
        "asset": "pump-015",
        "measurements": {
            "vibration": 16,
            "temperature": 98,
        },
        "findings": [
            "leak",
        ],
    }

    result = EnterpriseCognitivePipeline().run(reality)

    assert result["reality"]["object_id"] == "reality-015"

    assert result["observation"]["object_type"] == "observation"

    assert result["understanding"].enterprise_context["stage"] == "understanding"

    assert result["hypothesis"].enterprise_context["stage"] == "hypothesis"

    assert result["decision"].enterprise_context["stage"] == "decision"

    assert result["planning"].enterprise_context["stage"] == "planning"

    assert result["execution"].enterprise_context["stage"] == "execution"

    assert result["outcome"].enterprise_context["stage"] == "outcome"

    assert result["learning"].enterprise_context["stage"] == "learning"

    assert result["learning"].digital_thread_id == "reality-015"


def test_enterprise_cognitive_pipeline_preserves_digital_thread():

    reality = {
        "object_id": "reality-016",
        "object_type": "reality",
        "asset": "motor-016",
        "measurements": {
            "vibration": 5,
            "temperature": 65,
        },
        "findings": [],
    }

    result = EnterpriseCognitivePipeline().run(reality)

    assert result["understanding"].digital_thread_id == "reality-016"

    assert result["hypothesis"].digital_thread_id == "reality-016"

    assert result["decision"].digital_thread_id == "reality-016"

    assert result["planning"].digital_thread_id == "reality-016"

    assert result["execution"].digital_thread_id == "reality-016"

    assert result["outcome"].digital_thread_id == "reality-016"

    assert result["learning"].digital_thread_id == "reality-016"
