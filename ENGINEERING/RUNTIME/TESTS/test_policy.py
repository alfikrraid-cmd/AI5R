import pytest

from ENGINEERING.RUNTIME.contracts import CapabilityRequest
from ENGINEERING.RUNTIME.exceptions import PolicyViolation
from ENGINEERING.RUNTIME.policy import RuntimePolicy


def test_allowed_capability_passes_validation():
    policy = RuntimePolicy(allowed_capabilities=["hello"])
    request = CapabilityRequest(capability="hello", payload={})

    policy.validate(request)


def test_denied_capability_raises_policy_violation():
    policy = RuntimePolicy(allowed_capabilities=["hello"])
    request = CapabilityRequest(capability="docker", payload={})

    with pytest.raises(PolicyViolation):
        policy.validate(request)
