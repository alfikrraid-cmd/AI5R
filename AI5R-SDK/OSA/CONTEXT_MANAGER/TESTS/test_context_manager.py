import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.CONTEXT_MANAGER import ContextManager, ContextScope


def test_context_manager_creates_context():
    manager = ContextManager()

    context = manager.create(
        context_id="CTX-GOAL-001",
        scope=ContextScope.GOAL,
        owner_id="GOAL-001",
        data={"description": "Create campaign"},
    )

    assert context.context_id == "CTX-GOAL-001"
    assert context.scope == ContextScope.GOAL
    assert context.owner_id == "GOAL-001"
    assert context.data["description"] == "Create campaign"


def test_context_manager_updates_context():
    manager = ContextManager()

    manager.create(
        context_id="CTX-TASK-001",
        scope=ContextScope.TASK,
        owner_id="TASK-001",
        data={"status": "CREATED"},
    )

    updated = manager.update(
        "CTX-TASK-001",
        {"status": "RUNNING"},
    )

    assert updated.data["status"] == "RUNNING"


def test_context_manager_lists_by_owner():
    manager = ContextManager()

    manager.create(
        context_id="CTX-EMP-001",
        scope=ContextScope.EMPLOYEE,
        owner_id="EMP-001",
        data={"role": "Content"},
    )

    manager.create(
        context_id="CTX-EMP-002",
        scope=ContextScope.EMPLOYEE,
        owner_id="EMP-001",
        data={"capability": "ContentPlanning"},
    )

    assert len(manager.list_by_owner("EMP-001")) == 2


def test_context_manager_lists_by_scope():
    manager = ContextManager()

    manager.create(
        context_id="CTX-ORG-001",
        scope=ContextScope.ORGANIZATION,
        owner_id="ORG-001",
    )

    manager.create(
        context_id="CTX-GOAL-001",
        scope=ContextScope.GOAL,
        owner_id="GOAL-001",
    )

    assert len(manager.list_by_scope(ContextScope.ORGANIZATION)) == 1


def test_context_manager_merges_contexts():
    manager = ContextManager()

    manager.create(
        context_id="CTX-001",
        scope=ContextScope.TASK,
        owner_id="TASK-001",
        data={"task": "Create plan"},
    )

    manager.create(
        context_id="CTX-002",
        scope=ContextScope.EMPLOYEE,
        owner_id="EMP-001",
        data={"employee": "Content Agent"},
    )

    merged = manager.merge(
        context_ids=["CTX-001", "CTX-002"],
        merged_context_id="CTX-MERGED-001",
        scope=ContextScope.ORGANIZATION,
        owner_id="ORG-001",
    )

    assert merged.data["task"] == "Create plan"
    assert merged.data["employee"] == "Content Agent"


def test_context_manager_requires_context_id_and_owner_id():
    manager = ContextManager()

    try:
        manager.create(
            context_id="",
            scope=ContextScope.GOAL,
            owner_id="GOAL-001",
        )
    except ValueError as error:
        assert str(error) == "context_id is required"
    else:
        raise AssertionError("ValueError was not raised")

    try:
        manager.create(
            context_id="CTX-001",
            scope=ContextScope.GOAL,
            owner_id="",
        )
    except ValueError as error:
        assert str(error) == "owner_id is required"
    else:
        raise AssertionError("ValueError was not raised")


def test_context_manager_raises_when_context_missing():
    manager = ContextManager()

    try:
        manager.get("CTX-MISSING")
    except KeyError as error:
        assert str(error) == "'Context not found: CTX-MISSING'"
    else:
        raise AssertionError("KeyError was not raised")
