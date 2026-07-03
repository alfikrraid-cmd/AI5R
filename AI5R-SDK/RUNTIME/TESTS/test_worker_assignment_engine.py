import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from RUNTIME.enterprise_task import EnterpriseTask
from RUNTIME.enterprise_worker import EnterpriseWorker
from RUNTIME.worker_assignment_engine import WorkerAssignmentEngine


def test_worker_assignment_engine():
    engine = WorkerAssignmentEngine()

    worker = EnterpriseWorker(
        worker_type="knowledge",
        name="Knowledge Worker",
        capabilities=[
            "search_knowledge",
            "classify_issue",
        ],
    )

    engine.register(worker)

    task = EnterpriseTask(
        task_type="search_knowledge",
        title="Search Knowledge",
        instruction="Find relevant pump maintenance knowledge",
        mission_id="mission-001",
    )

    assigned_worker = engine.assign(task)

    assert assigned_worker is worker
    assert task.assigned_worker == worker.worker_id
    assert task.status == "assigned"


def test_worker_assignment_no_match():
    engine = WorkerAssignmentEngine()

    worker = EnterpriseWorker(
        worker_type="reporting",
        name="Reporting Worker",
        capabilities=[
            "generate_pdf_report",
        ],
    )

    engine.register(worker)

    task = EnterpriseTask(
        task_type="extract_pump_findings",
        title="Extract Pump Findings",
        instruction="Extract findings from uploaded pump report",
        mission_id="mission-001",
    )

    assigned_worker = engine.assign(task)

    assert assigned_worker is None
    assert task.assigned_worker is None
    assert task.status == "created"


if __name__ == "__main__":
    test_worker_assignment_engine()
    test_worker_assignment_no_match()
    print("EP-004 Worker Assignment Engine OK")
