import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from OS.identity_service import IdentityService


def test_register_identity():
    service = IdentityService()

    identity = service.register(
        "emp-001",
        "DIGITAL_EMPLOYEE",
        "Alice",
    )

    assert identity.identity_id == "emp-001"
    assert identity.identity_type == "DIGITAL_EMPLOYEE"


def test_duplicate_identity():
    service = IdentityService()

    service.register("emp-001", "DIGITAL_EMPLOYEE", "Alice")

    try:
        service.register("emp-001", "DIGITAL_EMPLOYEE", "Bob")
        assert False
    except ValueError:
        pass


def test_get_identity():
    service = IdentityService()

    service.register("emp-001", "DIGITAL_EMPLOYEE", "Alice")

    assert service.get("emp-001").name == "Alice"


def test_update_identity():
    service = IdentityService()

    service.register("emp-001", "DIGITAL_EMPLOYEE", "Alice")

    identity = service.update(
        "emp-001",
        {"department": "Finance"},
    )

    assert identity.attributes["department"] == "Finance"


def test_update_missing_identity():
    service = IdentityService()

    try:
        service.update("missing", {})
        assert False
    except ValueError:
        pass


def test_unregister_identity():
    service = IdentityService()

    service.register("emp-001", "DIGITAL_EMPLOYEE", "Alice")

    assert service.unregister("emp-001") is True
    assert service.get("emp-001") is None


def test_unregister_missing_identity():
    service = IdentityService()

    assert service.unregister("missing") is False


def test_list_identity():
    service = IdentityService()

    service.register("1", "EMPLOYEE", "A")
    service.register("2", "EMPLOYEE", "B")

    assert len(service.list()) == 2
