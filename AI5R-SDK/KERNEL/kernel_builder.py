from KERNEL.enterprise_kernel import EnterpriseKernel


class KernelBuilder:

    def build(
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

        return EnterpriseKernel(
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
