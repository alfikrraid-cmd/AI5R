class MarketingArtifact:
    domain_name = "MARKETING"

    def create(self, payload):
        return {
            "domain": self.domain_name,
            "layer": "Artifact",
            "status": "CREATED",
            "payload": payload,
        }
