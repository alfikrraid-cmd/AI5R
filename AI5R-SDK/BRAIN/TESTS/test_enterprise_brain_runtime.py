import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.enterprise_brain_runtime import EnterpriseBrainRuntime


def test_enterprise_brain_runtime_runs():

    reality = {
        "object_id": "reality-017",
        "object_type": "reality",
        "asset": "pump-017",
        "measurements": {
            "vibration": 17,
            "temperature": 99,
        },
        "findings": [
            "leak",
        ],
    }

    result = EnterpriseBrainRuntime().run(reality)

    assert result["status"] == "completed"

    assert result["runtime"] == "enterprise_brain_runtime"

    assert result["digital_thread_id"] == "reality-017"

    assert result["final_stage"] == "learning"

    assert result["learning"].enterprise_context["stage"] == "learning"

    assert result["trace"]["decision"].enterprise_context["stage"] == "decision"


def test_enterprise_brain_runtime_preserves_trace():

    reality = {
        "object_id": "reality-018",
        "object_type": "reality",
        "asset": "motor-018",
        "measurements": {
            "vibration": 5,
            "temperature": 65,
        },
        "findings": [],
    }

    result = EnterpriseBrainRuntime().run(reality)

    trace = result["trace"]

    assert trace["reality"]["object_id"] == "reality-018"

    assert trace["observation"]["object_type"] == "observation"

    assert trace["understanding"].digital_thread_id == "reality-018"

    assert trace["hypothesis"].digital_thread_id == "reality-018"

    assert trace["decision"].digital_thread_id == "reality-018"

    assert trace["planning"].digital_thread_id == "reality-018"

    assert trace["execution"].digital_thread_id == "reality-018"

    assert trace["outcome"].digital_thread_id == "reality-018"

    assert trace["learning"].digital_thread_id == "reality-018"
