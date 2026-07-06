import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE import EmployeeContext


def test_create_employee_context():
    context = EmployeeContext(
        employee_id="EMP-001",
        role="Marketing Manager",
        department="Marketing",
        organization="AI5R",
    )

    assert context.employee_id == "EMP-001"
    assert context.role == "Marketing Manager"
    assert context.department == "Marketing"
    assert context.organization == "AI5R"
    assert context.goals == []
    assert context.tasks == []


def test_add_goal_and_task():
    context = EmployeeContext(
        employee_id="EMP-002",
        role="Finance Manager",
        department="Finance",
        organization="AI5R",
    )

    context.add_goal("Increase revenue")
    context.add_task("Prepare monthly report")

    assert context.goals == ["Increase revenue"]
    assert context.tasks == ["Prepare monthly report"]
    assert context.updated_at is not None


def test_prevent_duplicate_goals_and_tasks():
    context = EmployeeContext(
        employee_id="EMP-003",
        role="CEO",
        department="Executive",
        organization="AI5R",
    )

    context.add_goal("Build AI5R OS")
    context.add_goal("Build AI5R OS")

    context.add_task("Lead sprint")
    context.add_task("Lead sprint")

    assert context.goals == ["Build AI5R OS"]
    assert context.tasks == ["Lead sprint"]


def test_memory_recall():
    context = EmployeeContext(
        employee_id="EMP-004",
        role="Researcher",
        department="Brain",
        organization="AI5R",
    )

    context.remember("market", "UMKM")
    context.remember("priority", 1)

    assert context.recall("market") == "UMKM"
    assert context.recall("priority") == 1
    assert context.recall("missing", "default") == "default"


def test_metadata_and_snapshot():
    context = EmployeeContext(
        employee_id="EMP-005",
        role="Operator",
        department="Execution",
        organization="AI5R",
    )

    context.update_metadata("level", "senior")

    snapshot = context.snapshot()

    assert snapshot["employee_id"] == "EMP-005"
    assert snapshot["metadata"]["level"] == "senior"
    assert snapshot["updated_at"] is not None
