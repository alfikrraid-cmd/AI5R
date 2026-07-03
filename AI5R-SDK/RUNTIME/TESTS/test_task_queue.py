import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from RUNTIME.enterprise_task import EnterpriseTask
from RUNTIME.task_queue import TaskQueue


def test_task_queue():
    queue = TaskQueue()

    assert queue.empty()
    assert queue.size() == 0

    task = EnterpriseTask(
        task_type="search_knowledge",
        title="Search Knowledge",
        instruction="Find relevant knowledge",
        mission_id="mission-001",
    )

    queue.enqueue(task)

    assert not queue.empty()
    assert queue.size() == 1

    dequeued = queue.dequeue()

    assert dequeued is task
    assert queue.empty()
    assert queue.size() == 0


if __name__ == "__main__":
    test_task_queue()
    print("EP-003 Task Queue OK")
