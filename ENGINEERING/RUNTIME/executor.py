from .contracts import Capability, CapabilityRequest
from .result import CapabilityResult


class CapabilityExecutor:
    """Executes a capability against a request. No business logic."""

    def execute(
        self,
        capability: Capability,
        request: CapabilityRequest,
    ) -> CapabilityResult:
        return capability.execute(request)
