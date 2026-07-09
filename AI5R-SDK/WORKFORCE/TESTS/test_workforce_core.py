from WORKFORCE.assignment import WorkAssignmentEngine, WorkOrder
from WORKFORCE.registry import WorkforceRegistry
from WORKFORCE.worker import Worker


def test_register_worker():
    registry = WorkforceRegistry()

    worker = Worker(
        worker_id="W-001",
        name="Backend Worker",
        role="BACKEND_ENGINEER",
        department="IT",
        skills=["Python", "FastAPI"],
    )

    registry.register(worker)

    assert registry.get("W-001").role == "BACKEND_ENGINEER"


def test_assign_work_order_to_available_worker():
    registry = WorkforceRegistry()
    registry.register(
        Worker(
            worker_id="W-001",
            name="Backend Worker",
            role="BACKEND_ENGINEER",
            department="IT",
            skills=["Python", "FastAPI"],
        )
    )

    engine = WorkAssignmentEngine(registry)

    assignment = engine.assign(
        WorkOrder(
            work_order_id="WO-001",
            objective="Implement authentication endpoint",
            required_role="BACKEND_ENGINEER",
            required_skills=["Python"],
        )
    )

    worker = registry.get("W-001")

    assert assignment.worker_id == "W-001"
    assert assignment.status == "ASSIGNED"
    assert worker.status == "BUSY"


def test_complete_assignment_updates_worker_experience_and_learning():
    registry = WorkforceRegistry()
    registry.register(
        Worker(
            worker_id="W-001",
            name="Backend Worker",
            role="BACKEND_ENGINEER",
            department="IT",
            skills=["Python"],
        )
    )

    engine = WorkAssignmentEngine(registry)

    assignment = engine.assign(
        WorkOrder(
            work_order_id="WO-002",
            objective="Implement JWT login",
            required_role="BACKEND_ENGINEER",
            required_skills=["Python"],
        )
    )

    completed = engine.complete(
        assignment,
        experience_object={
            "task": "JWT login implementation",
            "learned_skills": ["JWT"],
            "learned_capabilities": ["Authentication Pattern v1"],
        },
    )

    worker = registry.get("W-001")

    assert completed.status == "COMPLETED"
    assert worker.status == "AVAILABLE"
    assert "JWT" in worker.skills
    assert "Authentication Pattern v1" in worker.capabilities
    assert len(worker.experience) == 1


def test_busy_worker_cannot_receive_second_assignment():
    registry = WorkforceRegistry()
    registry.register(
        Worker(
            worker_id="W-001",
            name="Backend Worker",
            role="BACKEND_ENGINEER",
            department="IT",
            skills=["Python"],
        )
    )

    engine = WorkAssignmentEngine(registry)

    engine.assign(
        WorkOrder(
            work_order_id="WO-003",
            objective="Task one",
            required_role="BACKEND_ENGINEER",
            required_skills=["Python"],
        )
    )

    try:
        engine.assign(
            WorkOrder(
                work_order_id="WO-004",
                objective="Task two",
                required_role="BACKEND_ENGINEER",
                required_skills=["Python"],
            )
        )
    except ValueError as exc:
        assert "No available worker" in str(exc)
    else:
        raise AssertionError("Expected assignment to fail")
