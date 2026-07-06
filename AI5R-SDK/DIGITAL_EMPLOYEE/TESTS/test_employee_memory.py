from DIGITAL_EMPLOYEE.MEMORY import EmployeeMemory, EmployeeMemoryStore


def test_employee_memory_creation():
    memory = EmployeeMemory(
        employee_id="EMP-001",
        memory_type="TASK_RESULT",
        content={"status": "DONE"},
        metadata={"source": "unit-test"},
    )

    assert memory.memory_id.startswith("MEM-")
    assert memory.employee_id == "EMP-001"
    assert memory.memory_type == "TASK_RESULT"
    assert memory.content["status"] == "DONE"
    assert memory.metadata["source"] == "unit-test"
    assert memory.created_at


def test_employee_memory_rejects_missing_employee_id():
    try:
        EmployeeMemory(
            employee_id="",
            memory_type="TASK_RESULT",
            content={"status": "DONE"},
        )
    except ValueError as exc:
        assert "Employee ID is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_employee_memory_rejects_missing_memory_type():
    try:
        EmployeeMemory(
            employee_id="EMP-001",
            memory_type="",
            content={"status": "DONE"},
        )
    except ValueError as exc:
        assert "Memory type is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_employee_memory_rejects_missing_content():
    try:
        EmployeeMemory(
            employee_id="EMP-001",
            memory_type="TASK_RESULT",
            content=None,
        )
    except ValueError as exc:
        assert "Memory content is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_employee_memory_snapshot():
    memory = EmployeeMemory(
        employee_id="EMP-001",
        memory_type="NOTE",
        content="Remember client preference",
    )

    snapshot = memory.snapshot()

    assert snapshot["memory_id"] == memory.memory_id
    assert snapshot["employee_id"] == "EMP-001"
    assert snapshot["memory_type"] == "NOTE"
    assert snapshot["content"] == "Remember client preference"
    assert snapshot["metadata"] == {}
    assert snapshot["created_at"] == memory.created_at


def test_employee_memory_store_store_and_get():
    store = EmployeeMemoryStore()

    memory = store.store(
        employee_id="EMP-001",
        memory_type="TASK_RESULT",
        content={"status": "DONE"},
    )

    loaded = store.get(memory.memory_id)

    assert loaded is memory


def test_employee_memory_store_require_missing_memory():
    store = EmployeeMemoryStore()

    try:
        store.require("MEM-MISSING")
    except KeyError as exc:
        assert "Employee memory not found" in str(exc)
    else:
        raise AssertionError("Expected KeyError")


def test_employee_memory_store_list_by_employee():
    store = EmployeeMemoryStore()

    store.store("EMP-001", "NOTE", "A")
    store.store("EMP-001", "NOTE", "B")
    store.store("EMP-002", "NOTE", "C")

    memories = store.list("EMP-001")

    assert len(memories) == 2
    assert [memory.content for memory in memories] == ["A", "B"]


def test_employee_memory_store_list_by_type():
    store = EmployeeMemoryStore()

    store.store("EMP-001", "NOTE", "A")
    store.store("EMP-001", "TASK_RESULT", "B")
    store.store("EMP-001", "NOTE", "C")

    notes = store.list_by_type("EMP-001", "NOTE")

    assert len(notes) == 2
    assert [memory.content for memory in notes] == ["A", "C"]


def test_employee_memory_store_delete():
    store = EmployeeMemoryStore()

    memory = store.store("EMP-001", "NOTE", "A")

    deleted = store.delete(memory.memory_id)

    assert deleted is True
    assert store.get(memory.memory_id) is None
    assert store.count("EMP-001") == 0


def test_employee_memory_store_delete_missing_returns_false():
    store = EmployeeMemoryStore()

    assert store.delete("MEM-MISSING") is False


def test_employee_memory_store_count():
    store = EmployeeMemoryStore()

    store.store("EMP-001", "NOTE", "A")
    store.store("EMP-001", "NOTE", "B")
    store.store("EMP-002", "NOTE", "C")

    assert store.count() == 3
    assert store.count("EMP-001") == 2
    assert store.count("EMP-002") == 1


def test_employee_memory_store_snapshot_for_employee():
    store = EmployeeMemoryStore()

    store.store("EMP-001", "NOTE", "A")

    snapshot = store.snapshot("EMP-001")

    assert snapshot["employee_id"] == "EMP-001"
    assert snapshot["count"] == 1
    assert snapshot["memories"][0]["content"] == "A"


def test_employee_memory_store_snapshot_all():
    store = EmployeeMemoryStore()

    memory = store.store("EMP-001", "NOTE", "A")

    snapshot = store.snapshot()

    assert snapshot["count"] == 1
    assert snapshot["memories"][memory.memory_id]["content"] == "A"
