from EXECUTION.execution_runtime import ExecutionRuntime


class ExecutionPipeline:
    """
    AI5R Execution Pipeline

    Converts a plan into execution objects.
    """

    def __init__(self):
        self.execution_runtime = ExecutionRuntime()

    def create_from_plan(self, plan):
        if not plan:
            raise ValueError("Plan is required")

        executions = []

        for step in plan.execution_steps:
            result = self.execution_runtime.create(
                plan_id=plan.plan_id,
                step_number=step.get("step"),
                action=step.get("action"),
                capability_code=step.get("capability_code"),
                input_data=step.get("input_data", {}),
                metadata={
                    "mission_id": plan.mission_id,
                    "goal": plan.goal,
                },
            )

            executions.append(result["execution"])

        return {
            "status": "PIPELINE_CREATED",
            "plan_id": plan.plan_id,
            "executions": executions,
        }
