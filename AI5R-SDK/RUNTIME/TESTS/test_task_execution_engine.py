import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from RUNTIME.enterprise_task import EnterpriseTask
from RUNTIME.task_execution_engine import TaskExecutionEngine
from RUNTIME.TESTS.dummy_worker import DummyWorker


def test_execution():
    task = EnterpriseTask(
        task_type="search_knowledge",
        title="Search",
        instruction="Search",
        mission_id="mission-001",
    )

    worker = DummyWorker()
    engine = TaskExecutionEngine()

    result = engine.execute(worker, task)

    assert task.status == "completed"
    assert result["status"] == "success"
    assert result["worker"] == "dummy"


if __name__ == "__main__":
    test_execution()
    print("EP-005 Task Execution Engine OK")
