class ExecutionValidationEngine:
    """
    Enterprise Execution Validation Engine

    Validates execution completeness before runtime processing.
    """

    def validate(self, execution):
        errors = []

        if not execution.plan_id:
            errors.append("Plan ID is required")

        if not execution.step_number:
            errors.append("Step number is required")

        if not execution.action:
            errors.append("Action is required")

        if not execution.capability_code:
            errors.append("Capability code is required")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
