class EnterpriseIdentityGenerator:
    PREFIXES = {
        "enterprise": "ENT",
        "company": "COM",
        "brand": "BRD",
        "department": "DEP",
        "project": "PRJ",
        "customer": "CUS",
        "vendor": "VEN",
        "employee": "EMP",
        "asset": "AST",
        "bank_account": "BANK",
        "cost_center": "COST",
        "profit_center": "PROFIT",
    }

    def __init__(self):
        self._counters = {}

    def generate(self, object_type: str) -> str:
        if object_type not in self.PREFIXES:
            raise ValueError("unknown enterprise object type")

        self._counters[object_type] = self._counters.get(object_type, 0) + 1
        return f"{self.PREFIXES[object_type]}-{self._counters[object_type]:06d}"
