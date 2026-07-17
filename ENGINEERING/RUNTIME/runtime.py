from .contracts import CapabilityRequest
from .executor import CapabilityExecutor
from .policy import RuntimePolicy
from .registry import CapabilityRegistry
from .result import CapabilityResult


class EngineeringRuntime:
    """Executes engineering capabilities without knowing their internals.

    Flow: before_execute() -> Policy.validate() -> Registry.get()
    -> Executor.execute() -> Capability.execute() -> after_execute()
    -> CapabilityResult
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        policy: RuntimePolicy,
        executor: CapabilityExecutor,
    ) -> None:
        self.registry = registry
        self.policy = policy
        self.executor = executor

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        self._before_execute()

        self.policy.validate(request)

        capability = self.registry.get(request.capability)

        result = self.executor.execute(capability, request)

        self._after_execute()

        return result

    def _before_execute(self) -> None:
        """Hook reserved for future telemetry, auditing, and metrics."""

    def _after_execute(self) -> None:
        """Hook reserved for future telemetry, auditing, and metrics."""
