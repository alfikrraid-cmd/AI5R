class ExecutionRegistry:
    """
    Enterprise Execution Registry

    Stores and retrieves execution objects.
    """

    def __init__(self):
        self.executions = {}

    def register(self, execution):
        if not execution.execution_id:
            raise ValueError("Execution ID is required")

        self.executions[execution.execution_id] = execution

        return {
            "status": "REGISTERED",
            "execution_id": execution.execution_id,
        }

    def get(self, execution_id):
        return self.executions.get(execution_id)

    def list_all(self):
        return list(self.executions.values())

    def list_by_plan(self, plan_id):
        return [
            execution
            for execution in self.list_all()
            if execution.plan_id == plan_id
        ]

    def list_by_status(self, status):
        return [
            execution
            for execution in self.list_all()
            if execution.status == status
        ]
