class MarketingRuntime:
    domain_name = "MARKETING"

    def run(self, artifact):
        return {
            "domain": self.domain_name,
            "layer": "Runtime",
            "status": "RUNNING",
            "artifact": artifact,
        }
