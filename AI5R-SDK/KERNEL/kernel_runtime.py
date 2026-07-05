from KERNEL.kernel_builder import KernelBuilder
from KERNEL.kernel_health import KernelHealth
from KERNEL.kernel_registry import KernelRegistry


class KernelRuntime:

    def __init__(self):
        self.builder = KernelBuilder()
        self.health = KernelHealth()
        self.registry = KernelRegistry()

    def create(
        self,
        identity_runtime=None,
        organization_runtime=None,
        position_runtime=None,
        capability_runtime=None,
        mission_runtime=None,
        policy_runtime=None,
        knowledge_runtime=None,
        decision_runtime=None,
        execution_runtime=None,
    ):

        kernel = self.builder.build(
            identity_runtime=identity_runtime,
            organization_runtime=organization_runtime,
            position_runtime=position_runtime,
            capability_runtime=capability_runtime,
            mission_runtime=mission_runtime,
            policy_runtime=policy_runtime,
            knowledge_runtime=knowledge_runtime,
            decision_runtime=decision_runtime,
            execution_runtime=execution_runtime,
        )

        health = self.health.check(kernel)
        registration = self.registry.register(kernel)

        return {
            "status": "CREATED",
            "kernel": kernel,
            "health": health,
            "registration": registration,
        }

    def get(self, kernel_id):
        return self.registry.get(kernel_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_status(self, status):
        return self.registry.list_by_status(status)
