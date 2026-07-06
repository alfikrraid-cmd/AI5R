import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from OS.capability_service import CapabilityService


def test_register_capability():
    service = CapabilityService()

    capability = service.register(
        "cap-001",
        "emp-001",
        "Reasoning",
    )

    assert capability.capability_id == "cap-001"
    assert capability.identity_id == "emp-001"


def test_duplicate_capability():
    service = CapabilityService()

    service.register("cap-001", "emp-001", "Reasoning")

    try:
        service.register("cap-001", "emp-001", "Planning")
        assert False
    except ValueError:
        pass


def test_get_capability():
    service = CapabilityService()

    service.register("cap-001", "emp-001", "Reasoning")

    assert service.get("cap-001").capability_name == "Reasoning"


def test_list_capabilities():
    service = CapabilityService()

    service.register("1", "emp", "A")
    service.register("2", "emp", "B")

    assert len(service.list()) == 2


def test_list_by_identity():
    service = CapabilityService()

    service.register("1", "emp1", "A")
    service.register("2", "emp1", "B")
    service.register("3", "emp2", "C")

    assert len(service.list_by_identity("emp1")) == 2


def test_update_metadata():
    service = CapabilityService()

    service.register("1", "emp", "Reasoning")

    capability = service.update_metadata(
        "1",
        {"priority": "HIGH"},
    )

    assert capability.metadata["priority"] == "HIGH"


def test_update_missing():
    service = CapabilityService()

    try:
        service.update_metadata("missing", {})
        assert False
    except ValueError:
        pass


def test_unregister():
    service = CapabilityService()

    service.register("1", "emp", "Reasoning")

    assert service.unregister("1") is True
    assert service.get("1") is None


def test_unregister_missing():
    service = CapabilityService()

    assert service.unregister("missing") is False
