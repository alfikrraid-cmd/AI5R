class PlanningValidationEngine:
    """
    Enterprise Planning Validation Engine

    Validates plan completeness before execution.
    """

    def validate(self, plan):
        errors = []

        if not plan.mission_id:
            errors.append("Mission ID is required")

        if not plan.goal:
            errors.append("Goal is required")

        if not plan.execution_steps:
            errors.append("Execution steps are required")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
