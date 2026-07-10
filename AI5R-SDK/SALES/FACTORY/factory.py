class SalesFactory:
    domain_name = "SALES"

    def build(self, specification):
        return {
            "domain": self.domain_name,
            "layer": "Factory",
            "status": "BUILT",
            "specification": specification,
        }
