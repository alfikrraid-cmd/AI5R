import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from OS.resource_manager import ResourceManager


def test_register_resource():
    manager = ResourceManager()

    resource = manager.register(
        "res-001",
        "GPU",
        "runtime-01",
    )

    assert resource.resource_id == "res-001"
    assert resource.status == "AVAILABLE"


def test_duplicate_resource():
    manager = ResourceManager()

    manager.register("res-001", "GPU", "runtime")

    try:
        manager.register("res-001", "GPU", "runtime")
        assert False
    except ValueError:
        pass


def test_allocate_resource():
    manager = ResourceManager()

    manager.register("res-001", "GPU", "runtime")

    assert manager.allocate("res-001").status == "ALLOCATED"


def test_release_resource():
    manager = ResourceManager()

    manager.register("res-001", "GPU", "runtime")
    manager.allocate("res-001")

    assert manager.release("res-001").status == "AVAILABLE"


def test_list_by_owner():
    manager = ResourceManager()

    manager.register("1", "GPU", "runtime1")
    manager.register("2", "CPU", "runtime1")
    manager.register("3", "MEMORY", "runtime2")

    assert len(manager.list_by_owner("runtime1")) == 2


def test_unregister():
    manager = ResourceManager()

    manager.register("1", "GPU", "runtime")

    assert manager.unregister("1") is True
    assert manager.get("1") is None


def test_unregister_missing():
    manager = ResourceManager()

    assert manager.unregister("missing") is False


def test_allocate_missing():
    manager = ResourceManager()

    try:
        manager.allocate("missing")
        assert False
    except ValueError:
        pass


def test_release_missing():
    manager = ResourceManager()

    try:
        manager.release("missing")
        assert False
    except ValueError:
        pass
