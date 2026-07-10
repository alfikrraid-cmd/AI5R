class SalesSpecification:
    domain_name = "SALES"

    def describe(self):
        return {
            "domain": self.domain_name,
            "layer": "Specification",
            "status": "READY",
        }
