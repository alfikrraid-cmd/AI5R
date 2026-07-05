from EXECUTION.execution_engine import ExecutionEngine
from EXECUTION.execution_registry import ExecutionRegistry


class ExecutionRuntime:
    """
    Enterprise Execution Runtime

    Creates, registers, and manages execution objects.
    """

    def __init__(self):
        self.engine = ExecutionEngine()
        self.registry = ExecutionRegistry()

    def create(
        self,
        plan_id,
        step_number,
        action,
        capability_code,
        input_data=None,
        metadata=None,
    ):
        execution = self.engine.create_execution(
            plan_id=plan_id,
            step_number=step_number,
            action=action,
            capability_code=capability_code,
            input_data=input_data,
            metadata=metadata,
        )

        registration = self.registry.register(execution)

        return {
            "status": "CREATED",
            "registration": registration,
            "execution": execution,
        }

    def get(self, execution_id):
        return self.registry.get(execution_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_plan(self, plan_id):
        return self.registry.list_by_plan(plan_id)

    def list_by_status(self, status):
        return self.registry.list_by_status(status)
