"""Example demo of DockerCapability executing GET_VERSION through the
unmodified Engineering Runtime."""

from ENGINEERING.RUNTIME.contracts import CapabilityRequest
from ENGINEERING.RUNTIME.executor import CapabilityExecutor
from ENGINEERING.RUNTIME.policy import RuntimePolicy
from ENGINEERING.RUNTIME.registry import CapabilityRegistry
from ENGINEERING.RUNTIME.runtime import EngineeringRuntime

from ENGINEERING.CAPABILITIES.DOCKER.capability import DockerCapability


def main() -> None:
    registry = CapabilityRegistry()
    registry.register(DockerCapability())

    policy = RuntimePolicy(allowed_capabilities=["docker"])
    executor = CapabilityExecutor()

    runtime = EngineeringRuntime(registry=registry, policy=policy, executor=executor)

    result = runtime.execute(
        CapabilityRequest(
            capability="docker",
            payload={"operation": "GET_VERSION"},
        )
    )

    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"stdout: {result.payload.get('stdout')}")
    print(f"duration: {result.duration}s")


if __name__ == "__main__":
    main()
