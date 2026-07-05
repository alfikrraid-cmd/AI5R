class PipelineValidationEngine:
    """
    AI5R Pipeline Validation Engine

    Validates whether a plan is ready to be converted
    into execution objects.
    """

    def validate_plan(self, plan):
        errors = []

        if not plan:
            errors.append("Plan is required")
            return {
                "valid": False,
                "errors": errors,
            }

        if not plan.plan_id:
            errors.append("Plan ID is required")

        if not plan.mission_id:
            errors.append("Mission ID is required")

        if not plan.goal:
            errors.append("Goal is required")

        if not plan.execution_steps:
            errors.append("Execution steps are required")

        for index, step in enumerate(plan.execution_steps, start=1):
            if not step.get("step"):
                errors.append(f"Step number is required at index {index}")

            if not step.get("action"):
                errors.append(f"Action is required at index {index}")

            if not step.get("capability_code"):
                errors.append(f"Capability code is required at index {index}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
