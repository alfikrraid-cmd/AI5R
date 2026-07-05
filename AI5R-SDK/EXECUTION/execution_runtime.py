from EXECUTION.execution_engine import ExecutionEngine
from EXECUTION.execution_registry import ExecutionRegistry


class ExecutionRuntime:
    def __init__(self):
        self.engine = ExecutionEngine()
        self.registry = ExecutionRegistry()

    def create(
        self,
        plan_id: str,
        step_number: int,
        action: str,
        capability_code: str,
        input_data: dict,
        metadata: dict | None = None,
        capability_id: str = "CAPABILITY-DEFAULT",
    ):
        execution = self.engine.create_execution(
            plan_id=plan_id,
            step_number=step_number,
            action=action,
            capability_code=capability_code,
            input_data=input_data,
            metadata=metadata or {},
            capability_id=capability_id if capability_id != "CAPABILITY-DEFAULT" else capability_code,
        )

        registration = self.registry.register(execution)

        return {
            "status": "CREATED",
            "execution": execution,
            "registration": registration,
        }


    def get(self, execution_id):
        return self.registry.get(execution_id)

    def list_all(self):
        return self.registry.list_all()

# Runtime registry proxy compatibility
def _runtime_list_by_plan(self, plan_id):
    return self.registry.list_by_plan(plan_id)

def _runtime_list_by_status(self, status):
    return self.registry.list_by_status(status)

ExecutionRuntime.list_by_plan = _runtime_list_by_plan
ExecutionRuntime.list_by_status = _runtime_list_by_status
