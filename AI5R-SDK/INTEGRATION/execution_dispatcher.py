from CAPABILITY.capability_runtime import CapabilityRuntime


class ExecutionDispatcher:
    """
    AI5R Execution Dispatcher

    Dispatches execution objects to the Capability Runtime.
    """

    def __init__(self):
        self.capability_runtime = CapabilityRuntime()

    def dispatch(self, execution):
        if execution is None:
            raise ValueError("Execution object is required")

        result = self.capability_runtime.execute(
            capability_id=execution.capability_id,
            input_data=execution.input_data,
        )

        return {
            "status": "DISPATCHED",
            "execution_id": execution.execution_id,
            "capability_result": result,
        }
