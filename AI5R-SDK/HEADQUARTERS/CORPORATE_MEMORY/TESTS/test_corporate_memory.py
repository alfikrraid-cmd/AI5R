from dataclasses import FrozenInstanceError

from HEADQUARTERS.CORPORATE_MEMORY import (
    MemoryObject,
    MemoryQuery,
    MemoryRegistry,
    MemoryRepository,
)


def _memory(
    mission_id="MISSION-001",
    mission_title="Build Restaurant ERP",
    executive="Raid",
):
    return MemoryObject(
        mission_id=mission_id,
        mission_title=mission_title,
        executive=executive,
        decision="APPROVED",
        outcome="SUCCESS",
        lessons_learned=[
            "Start with MVP",
            "Validate business value early",
        ],
        confidence=92,
    )


def test_memory_object_snapshot():
    memory = _memory()

    snapshot = memory.snapshot()

    assert snapshot["memory_id"].startswith("MEM-")
    assert snapshot["mission_id"] == "MISSION-001"
    assert snapshot["mission_title"] == "Build Restaurant ERP"
    assert snapshot["executive"] == "Raid"
    assert snapshot["decision"] == "APPROVED"
    assert snapshot["outcome"] == "SUCCESS"
    assert snapshot["confidence"] == 92


def test_memory_object_is_immutable():
    memory = _memory()

    try:
        memory.outcome = "FAILED"
    except FrozenInstanceError:
        assert True
    else:
        raise AssertionError("MemoryObject must be immutable")


def test_memory_registry_registers_and_gets_memory():
    registry = MemoryRegistry()
    memory = registry.register(_memory())

    assert registry.get(memory.memory_id) == memory
    assert len(registry.all()) == 1


def test_memory_query_by_mission_id():
    registry = MemoryRegistry()
    registry.register(_memory(mission_id="MISSION-001"))
    registry.register(_memory(mission_id="MISSION-002"))

    result = MemoryQuery(registry).by_mission_id("MISSION-001")

    assert len(result) == 1
    assert result[0]["mission_id"] == "MISSION-001"


def test_memory_query_by_executive():
    registry = MemoryRegistry()
    registry.register(_memory(executive="Raid"))
    registry.register(_memory(executive="Jazari"))

    result = MemoryQuery(registry).by_executive("Jazari")

    assert len(result) == 1
    assert result[0]["executive"] == "Jazari"


def test_memory_query_search_title():
    registry = MemoryRegistry()
    registry.register(_memory(mission_title="Build Restaurant ERP"))
    registry.register(_memory(mission_title="Build Clinic CRM"))

    result = MemoryQuery(registry).search_title("restaurant")

    assert len(result) == 1
    assert result[0]["mission_title"] == "Build Restaurant ERP"


def test_memory_repository_snapshot():
    repository = MemoryRepository()
    repository.save(_memory())

    snapshot = repository.snapshot()

    assert len(snapshot) == 1
    assert snapshot[0]["outcome"] == "SUCCESS"
