class FactoryValidator:
    """
    Validates manufacturing definitions before compilation.
    """

    REQUIRED_FIELDS = [
        "product",
        "version",
        "factory",
    ]

    def validate(self, definition: dict) -> dict:
        errors = []

        for field in self.REQUIRED_FIELDS:
            if field not in definition:
                errors.append(f"Missing required field: {field}")

        if errors:
            return {
                "status": "INVALID",
                "errors": errors,
            }

        return {
            "status": "VALID",
            "errors": [],
        }
