from KERNEL.kernel_pipeline import KernelPipeline
from KERNEL.kernel_response_builder import KernelResponseBuilder


class KernelOrchestrator:

    def __init__(self):
        self.pipeline = KernelPipeline()
        self.response_builder = KernelResponseBuilder()

    def handle(
        self,
        kernel,
        user_input: str,
        identity_context: dict | None = None,
        position_context: dict | None = None,
        decision_context: dict | None = None,
        execution_context: dict | None = None,
        decision_result: dict | None = None,
        execution_result: dict | None = None,
        metadata: dict | None = None,
    ):

        pipeline_result = self.pipeline.run(
            kernel=kernel,
            user_input=user_input,
            identity_context=identity_context or {},
            position_context=position_context or {},
            decision_context=decision_context or {},
            execution_context=execution_context or {},
            metadata=metadata or {},
        )

        context = pipeline_result["context"]

        response = self.response_builder.build(
            context=context,
            decision_result=decision_result or {},
            execution_result=execution_result or {},
        )

        return {
            "status": "ORCHESTRATED",
            "kernel_id": kernel.kernel_id,
            "pipeline": pipeline_result,
            "response": response,
        }
