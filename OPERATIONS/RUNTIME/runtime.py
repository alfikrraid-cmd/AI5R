class OperationsRuntime:
    domain_name = "OPERATIONS"

    def run(self, artifact):
        return {
            "domain": self.domain_name,
            "layer": "Runtime",
            "status": "RUNNING",
            "artifact": artifact,
        }
