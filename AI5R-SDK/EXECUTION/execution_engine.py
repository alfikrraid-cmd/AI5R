from EXECUTION.execution_object import ExecutionObject


class ExecutionEngine:
    def create_execution(
        self,
        plan_id: str,
        step_number: int,
        action: str,
        capability_code: str,
        input_data: dict,
        metadata: dict | None = None,
        capability_id: str = "CAPABILITY-DEFAULT",
    ) -> ExecutionObject:
        return ExecutionObject(
            plan_id=plan_id,
            step_number=step_number,
            action=action,
            capability_code=capability_code,
            input_data=input_data,
            metadata=metadata or {},
            capability_id=capability_id if capability_id != "CAPABILITY-DEFAULT" else capability_code,
        )
