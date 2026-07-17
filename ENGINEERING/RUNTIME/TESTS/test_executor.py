from ENGINEERING.RUNTIME.contracts import CapabilityRequest
from ENGINEERING.RUNTIME.executor import CapabilityExecutor
from ENGINEERING.RUNTIME.TESTS.test_contracts import HelloCapability


def test_executor_calls_capability_execute():
    executor = CapabilityExecutor()
    capability = HelloCapability()
    request = CapabilityRequest(capability="hello", payload={})

    result = executor.execute(capability, request)

    assert result.message == "hello"


def test_executor_delegates_without_business_logic(monkeypatch):
    executor = CapabilityExecutor()
    capability = HelloCapability()
    request = CapabilityRequest(capability="hello", payload={})

    calls = []
    original_execute = capability.execute

    def tracking_execute(req):
        calls.append(req)
        return original_execute(req)

    monkeypatch.setattr(capability, "execute", tracking_execute)

    executor.execute(capability, request)

    assert calls == [request]
