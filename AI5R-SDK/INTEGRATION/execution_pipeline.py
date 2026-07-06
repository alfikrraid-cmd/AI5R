from EXECUTION.execution_runtime import ExecutionRuntime
from INTEGRATION.pipeline_validation_engine import PipelineValidationEngine


class ExecutionPipeline:
    """
    AI5R Execution Pipeline

    Validates and converts a plan into execution objects.
    """

    def __init__(self):
        self.execution_runtime = ExecutionRuntime()
        self.validator = PipelineValidationEngine()

    def create_from_plan(self, plan):
        validation = self.validator.validate_plan(plan)

        if not validation["valid"]:
            return {
                "status": "INVALID_PLAN",
                "validation": validation,
                "executions": [],
            }

        executions = []

        for step in plan.execution_steps:
            result = self.execution_runtime.create(
                plan_id=plan.plan_id,
                step_number=step.get("step"),
                action=step.get("action"),
                capability_id=step.get("capability_id") or step.get("capability_code"),
                capability_code=step.get("capability_code", ""),
                input_data=step.get("input_data", {}),
                metadata={
                    "mission_id": plan.mission_id,
                    "goal": plan.goal,
                },
            )

            executions.append(result["execution"])

        return {
            "status": "PIPELINE_CREATED",
            "validation": validation,
            "plan_id": plan.plan_id,
            "executions": executions,
        }
