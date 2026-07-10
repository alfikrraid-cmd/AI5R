class OperationsArtifact:
    domain_name = "OPERATIONS"

    def create(self, payload):
        return {
            "domain": self.domain_name,
            "layer": "Artifact",
            "status": "CREATED",
            "payload": payload,
        }
