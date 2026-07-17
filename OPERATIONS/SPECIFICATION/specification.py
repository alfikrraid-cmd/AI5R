class OperationsSpecification:
    domain_name = "OPERATIONS"

    def describe(self):
        return {
            "domain": self.domain_name,
            "layer": "Specification",
            "status": "READY",
        }
