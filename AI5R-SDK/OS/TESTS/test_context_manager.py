import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from OS.context_manager import ContextManager, OSContext


def test_context_manager_creates_context():
    manager = ContextManager()

    context = manager.create_context(
        process_id="proc-001",
        data={"task": "manufacture"},
        metadata={"source": "test"},
    )

    assert isinstance(context, OSContext)
    assert context.context_id == "ctx-proc-001"
    assert context.process_id == "proc-001"
    assert context.scope == "PROCESS"
    assert context.data["task"] == "manufacture"
    assert context.metadata["source"] == "test"


def test_context_manager_requires_process_id():
    manager = ContextManager()

    try:
        manager.create_context(process_id="")
        assert False
    except ValueError as error:
        assert str(error) == "process_id is required"


def test_context_manager_gets_context_by_id():
    manager = ContextManager()
    created = manager.create_context(process_id="proc-002")

    found = manager.get_context(created.context_id)

    assert found == created


def test_context_manager_gets_process_context():
    manager = ContextManager()
    created = manager.create_context(process_id="proc-003")

    found = manager.get_process_context("proc-003")

    assert found == created


def test_context_manager_updates_context():
    manager = ContextManager()
    context = manager.create_context(
        process_id="proc-004",
        data={"state": "created"},
    )

    updated = manager.update_context(
        context.context_id,
        data={"state": "running"},
        metadata={"owner": "os"},
    )

    assert updated.data["state"] == "running"
    assert updated.metadata["owner"] == "os"
    assert updated.updated_at >= updated.created_at


def test_context_manager_raises_when_updating_missing_context():
    manager = ContextManager()

    try:
        manager.update_context("ctx-missing", data={"x": 1})
        assert False
    except ValueError as error:
        assert str(error) == "context not found"


def test_context_manager_deletes_context():
    manager = ContextManager()
    context = manager.create_context(process_id="proc-005")

    deleted = manager.delete_context(context.context_id)

    assert deleted is True
    assert manager.get_context(context.context_id) is None


def test_context_manager_returns_false_when_deleting_missing_context():
    manager = ContextManager()

    deleted = manager.delete_context("ctx-missing")

    assert deleted is False


def test_context_manager_lists_contexts():
    manager = ContextManager()
    manager.create_context(process_id="proc-006")
    manager.create_context(process_id="proc-007")

    contexts = manager.list_contexts()

    assert len(contexts) == 2
