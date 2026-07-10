class MarketingFactory:
    domain_name = "MARKETING"

    def build(self, specification):
        return {
            "domain": self.domain_name,
            "layer": "Factory",
            "status": "BUILT",
            "specification": specification,
        }
