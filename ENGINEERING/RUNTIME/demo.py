"""Example demo of the Engineering Runtime Core executing HelloCapability."""

from ENGINEERING.RUNTIME.contracts import Capability, CapabilityRequest
from ENGINEERING.RUNTIME.executor import CapabilityExecutor
from ENGINEERING.RUNTIME.policy import RuntimePolicy
from ENGINEERING.RUNTIME.registry import CapabilityRegistry
from ENGINEERING.RUNTIME.result import CapabilityResult
from ENGINEERING.RUNTIME.runtime import EngineeringRuntime


class HelloCapability(Capability):
    capability_code = "hello"
    capability_name = "Hello Capability"

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        return CapabilityResult.success(message="hello")


def main() -> None:
    registry = CapabilityRegistry()
    registry.register(HelloCapability())

    policy = RuntimePolicy(allowed_capabilities=["hello"])
    executor = CapabilityExecutor()

    runtime = EngineeringRuntime(registry=registry, policy=policy, executor=executor)

    result = runtime.execute(CapabilityRequest(capability="hello", payload={}))

    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"duration: {result.duration}s")


if __name__ == "__main__":
    main()
