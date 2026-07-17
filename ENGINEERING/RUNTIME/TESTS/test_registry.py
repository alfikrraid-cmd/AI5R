import pytest

from ENGINEERING.RUNTIME.exceptions import CapabilityNotFound
from ENGINEERING.RUNTIME.registry import CapabilityRegistry
from ENGINEERING.RUNTIME.TESTS.test_contracts import HelloCapability


def test_register_and_get():
    registry = CapabilityRegistry()
    capability = HelloCapability()

    registry.register(capability)

    assert registry.get("hello") is capability


def test_get_missing_capability_raises():
    registry = CapabilityRegistry()

    with pytest.raises(CapabilityNotFound):
        registry.get("does-not-exist")


def test_unregister_removes_capability():
    registry = CapabilityRegistry()
    registry.register(HelloCapability())

    registry.unregister("hello")

    with pytest.raises(CapabilityNotFound):
        registry.get("hello")


def test_unregister_missing_capability_raises():
    registry = CapabilityRegistry()

    with pytest.raises(CapabilityNotFound):
        registry.unregister("does-not-exist")


def test_list_returns_all_registered_capabilities():
    registry = CapabilityRegistry()
    capability = HelloCapability()
    registry.register(capability)

    result = registry.list()

    assert result == [capability]


def test_load_builtin_is_not_implemented():
    registry = CapabilityRegistry()

    with pytest.raises(NotImplementedError):
        registry.load_builtin()


def test_load_package_is_not_implemented():
    registry = CapabilityRegistry()

    with pytest.raises(NotImplementedError):
        registry.load_package()
