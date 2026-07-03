import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from RUNTIME.enterprise_task import EnterpriseTask
from RUNTIME.worker_assignment_engine import WorkerAssignmentEngine


def test_worker_assignment_engine():
    engine = WorkerAssignmentEngine()

    engine.register_worker(
        "worker-knowledge-engine",
        ["search_knowledge", "classify_issue"],
    )

    engine.register_worker(
        "worker-reporting-engine",
        ["generate_pdf_report"],
    )

    task = EnterpriseTask(
        task_type="search_knowledge",
        title="Search Knowledge",
        instruction="Find relevant pump maintenance knowledge",
        mission_id="mission-001",
    )

    assigned_worker = engine.assign(task)

    assert assigned_worker == "worker-knowledge-engine"
    assert task.assigned_worker == "worker-knowledge-engine"
    assert task.status == "assigned"


def test_worker_assignment_no_match():
    engine = WorkerAssignmentEngine()

    engine.register_worker(
        "worker-reporting-engine",
        ["generate_pdf_report"],
    )

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
