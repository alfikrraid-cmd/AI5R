from ENGINEERING.RUNTIME.contracts import Capability, CapabilityRequest
from ENGINEERING.RUNTIME.result import CapabilityResult, CapabilityStatus


class HelloCapability(Capability):
    capability_code = "hello"
    capability_name = "Hello Capability"

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        return CapabilityResult.success(
            message="hello",
            payload={"greeting": "hello"},
        )


def test_hello_capability_executes_successfully():
    capability = HelloCapability()
    request = CapabilityRequest(capability="hello", payload={})

    result = capability.execute(request)

    assert result.status == CapabilityStatus.SUCCESS
    assert result.message == "hello"


def test_capability_request_defaults_metadata_to_empty_dict():
    request = CapabilityRequest(capability="hello", payload={})

    assert request.metadata == {}


def test_capability_request_defaults_context_to_empty_dict():
    request = CapabilityRequest(capability="hello", payload={})

    assert request.context == {}


def test_capability_status_includes_cancelled():
    assert CapabilityStatus.CANCELLED == "CANCELLED"
