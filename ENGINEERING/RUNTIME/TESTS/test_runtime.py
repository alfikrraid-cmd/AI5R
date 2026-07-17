import pytest

from ENGINEERING.RUNTIME.contracts import CapabilityRequest
from ENGINEERING.RUNTIME.executor import CapabilityExecutor
from ENGINEERING.RUNTIME.exceptions import CapabilityNotFound, PolicyViolation
from ENGINEERING.RUNTIME.policy import RuntimePolicy
from ENGINEERING.RUNTIME.registry import CapabilityRegistry
from ENGINEERING.RUNTIME.result import CapabilityStatus
from ENGINEERING.RUNTIME.runtime import EngineeringRuntime
from ENGINEERING.RUNTIME.TESTS.test_contracts import HelloCapability


def build_runtime(allowed_capabilities):
    registry = CapabilityRegistry()
    registry.register(HelloCapability())

    policy = RuntimePolicy(allowed_capabilities=allowed_capabilities)
    executor = CapabilityExecutor()

    return EngineeringRuntime(registry=registry, policy=policy, executor=executor)


def test_runtime_executes_registered_capability():
    runtime = build_runtime(allowed_capabilities=["hello"])
    request = CapabilityRequest(capability="hello", payload={})

    result = runtime.execute(request)

    assert result.status == CapabilityStatus.SUCCESS
    assert result.message == "hello"


def test_runtime_raises_policy_violation_for_disallowed_capability():
    runtime = build_runtime(allowed_capabilities=[])
    request = CapabilityRequest(capability="hello", payload={})

    with pytest.raises(PolicyViolation):
        runtime.execute(request)


def test_runtime_raises_capability_not_found_for_unregistered_capability():
    runtime = build_runtime(allowed_capabilities=["docker"])
    request = CapabilityRequest(capability="docker", payload={})

    with pytest.raises(CapabilityNotFound):
        runtime.execute(request)


def test_runtime_hooks_are_called_around_execution():
    runtime = build_runtime(allowed_capabilities=["hello"])
    request = CapabilityRequest(capability="hello", payload={})

    calls = []
    runtime._before_execute = lambda: calls.append("before")
    runtime._after_execute = lambda: calls.append("after")

    runtime.execute(request)

    assert calls == ["before", "after"]


def test_runtime_default_hooks_are_noop():
    runtime = build_runtime(allowed_capabilities=["hello"])

    assert runtime._before_execute() is None
    assert runtime._after_execute() is None
