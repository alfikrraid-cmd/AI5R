class SalesArtifact:
    domain_name = "SALES"

    def create(self, payload):
        return {
            "domain": self.domain_name,
            "layer": "Artifact",
            "status": "CREATED",
            "payload": payload,
        }
