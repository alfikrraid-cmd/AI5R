class KernelHealth:

    REQUIRED_COMPONENTS = [
        "identity_runtime",
        "position_runtime",
        "decision_runtime",
        "execution_runtime",
    ]

    def check(self, kernel):

        missing = [
            component
            for component in self.REQUIRED_COMPONENTS
            if getattr(kernel, component) is None
        ]

        if missing:
            return {
                "status": "UNHEALTHY",
                "missing": missing,
            }

        return {
            "status": "HEALTHY",
            "missing": [],
        }
