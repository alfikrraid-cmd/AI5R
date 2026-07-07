from OSA.TASK_ENGINE.universal_task_engine import UniversalTaskEngine
from OSA.TASK_ENGINE.task_status import TaskStatus


def test_submit_creates_ready_task():
    engine = UniversalTaskEngine()

    task = engine.submit(
        goal="Create marketing strategy",
        employee_id="EMP-001",
    )

    assert task.goal == "Create marketing strategy"
    assert task.employee_id == "EMP-001"
    assert task.status == TaskStatus.READY
    assert task.task_id.startswith("TASK-")


def test_submit_publishes_event():
    engine = UniversalTaskEngine()

    engine.submit("Build sales campaign")

    events = engine.event_bus.list_events()

    assert len(events) == 1
    assert events[0]["event"] == "TASK_CREATED"
    assert events[0]["module"] == "TASK_ENGINE"


def test_submit_includes_goal_decomposition():
    engine = UniversalTaskEngine()

    task = engine.submit("Create marketing strategy for UMKM batik")

    assert task.goal_id.startswith("GOAL-")
    assert len(task.subtasks) >= 5

    events = engine.event_bus.list_events()
    assert events[0]["payload"]["goal_id"] == task.goal_id
    assert len(events[0]["payload"]["subtasks"]) >= 5
