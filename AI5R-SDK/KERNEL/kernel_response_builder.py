class KernelResponseBuilder:

    def build(
        self,
        context,
        decision_result: dict | None = None,
        execution_result: dict | None = None,
    ):

        return {
            "status": "RESPONSE_BUILT",
            "context_id": context.context_id,
            "kernel_id": context.kernel_id,
            "user_input": context.user_input,
            "identity_context": context.identity_context,
            "position_context": context.position_context,
            "decision_result": decision_result or {},
            "execution_result": execution_result or {},
        }
