from BUSINESS.business_catalog import BusinessCatalog
from BUSINESS.business_engine import BusinessEngine
from BUSINESS.pricing_engine import PricingEngine


class BusinessRuntime:

    def __init__(self):
        self.catalog = BusinessCatalog()
        self.business_engine = BusinessEngine()
        self.pricing_engine = PricingEngine()

    def register(self, item):
        return self.catalog.register(item)

    def build_business_model(self, business_model):
        result = self.business_engine.build(business_model)
        registration = self.catalog.register(business_model)

        return {
            "status": "CREATED",
            "result": result,
            "registration": registration,
        }

    def calculate_pricing(self, pricing, used_units: int = 0):
        result = self.pricing_engine.calculate(
            pricing=pricing,
            used_units=used_units,
        )

        return result

    def get(self, item_id):
        return self.catalog.get(item_id)

    def list_all(self):
        return self.catalog.list_all()

    def list_by_type(self, object_type):
        return self.catalog.list_by_type(object_type)

    def list_by_product(self, product_code):
        return self.catalog.list_by_product(product_code)
