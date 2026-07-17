class OperationsFactory:
    domain_name = "OPERATIONS"

    def build(self, specification):
        return {
            "domain": self.domain_name,
            "layer": "Factory",
            "status": "BUILT",
            "specification": specification,
        }
