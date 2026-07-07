import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.API.command_api import OSACommandAPI


def test_runtime_end_to_end_command_execution():
    api = OSACommandAPI()

    result = api.execute(
        prompt="Create UMKM digital marketing strategy",
        employee_id="EMP-001",
    )

    assert result["status"] == "SUCCESS"
    assert result["employee_id"] == "EMP-001"

    assert result["pipeline_id"].startswith("PIPE-CMD-")
    assert result["goal_id"].startswith("CMD-")
    assert result["task_count"] >= 1
    assert result["execution_count"] == result["task_count"]
    assert result["memory_count"] == result["task_count"]

    assert len(result["memories"]) == result["memory_count"]

    first_memory = result["memories"][0]

    assert hasattr(first_memory, "status")
    assert first_memory.status.value == "LEARNED"
