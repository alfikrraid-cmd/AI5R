from KERNEL.kernel_context import KernelContext


class KernelPipeline:

    def run(
        self,
        kernel,
        user_input: str,
        identity_context: dict | None = None,
        position_context: dict | None = None,
        decision_context: dict | None = None,
        execution_context: dict | None = None,
        metadata: dict | None = None,
    ):

        context = KernelContext(
            kernel_id=kernel.kernel_id,
            user_input=user_input,
            identity_context=identity_context or {},
            position_context=position_context or {},
            decision_context=decision_context or {},
            execution_context=execution_context or {},
            metadata=metadata or {},
        )

        return {
            "status": "PIPELINE_COMPLETED",
            "kernel_id": kernel.kernel_id,
            "context": context,
        }
