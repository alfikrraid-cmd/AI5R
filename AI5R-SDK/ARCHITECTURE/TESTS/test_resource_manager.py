import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import ResourceManager


def test_register_resource():
    manager = ResourceManager()

    resource = manager.register(
        resource_id="EMP-001",
        resource_type="EMPLOYEE",
        resource=object(),
    )

    assert resource.resource_id == "EMP-001"
    assert manager.get("EMP-001") is resource


def test_allocate_and_release():
    manager = ResourceManager()

    manager.register(
        "BUS",
        "SERVICE",
        object(),
    )

    resource = manager.allocate("BUS")

    assert resource.allocated is True
    assert resource.allocated_at is not None

    resource = manager.release("BUS")

    assert resource.allocated is False
    assert resource.released_at is not None


def test_allocated_resources():
    manager = ResourceManager()

    manager.register("A", "SERVICE", object())
    manager.register("B", "SERVICE", object())

    manager.allocate("A")

    allocated = manager.allocated()

    assert len(allocated) == 1
    assert allocated[0].resource_id == "A"


def test_summary():
    manager = ResourceManager()

    manager.register("A", "SERVICE", object())
    manager.register("B", "SERVICE", object())

    manager.allocate("B")

    summary = manager.summary()

    assert summary["registered"] == 2
    assert summary["allocated"] == 1
    assert summary["available"] == 1
