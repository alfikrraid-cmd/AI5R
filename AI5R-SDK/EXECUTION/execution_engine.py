from EXECUTION.execution_object import ExecutionObject


class ExecutionEngine:
    """
    Enterprise Execution Engine

    Converts a plan step into an execution object.
    """

    def create_execution(
        self,
        plan_id,
        step_number,
        action,
        capability_code,
        input_data=None,
        metadata=None,
    ):
        if not plan_id:
            raise ValueError("Plan ID is required")

        if not step_number:
            raise ValueError("Step number is required")

        if not action:
            raise ValueError("Action is required")

        if not capability_code:
            raise ValueError("Capability code is required")

        return ExecutionObject(
            plan_id=plan_id,
            step_number=step_number,
            action=action,
            capability_code=capability_code,
            input_data=input_data or {},
            metadata=metadata or {},
        )
