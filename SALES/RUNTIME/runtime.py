class SalesRuntime:
    domain_name = "SALES"

    def run(self, artifact):
        return {
            "domain": self.domain_name,
            "layer": "Runtime",
            "status": "RUNNING",
            "artifact": artifact,
        }
