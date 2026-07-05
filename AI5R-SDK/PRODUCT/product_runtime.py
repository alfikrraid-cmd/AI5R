from PRODUCT.product_engine import ProductEngine
from PRODUCT.product_catalog import ProductCatalog


class ProductRuntime:

    def __init__(self):
        self.engine = ProductEngine()
        self.catalog = ProductCatalog()

    def create(
        self,
        product,
    ):

        result = self.engine.build(product)
        registration = self.catalog.register(result)

        return {
            "status": "CREATED",
            "product": product,
            "result": result,
            "registration": registration,
        }

    def get(self, product_id):
        return self.catalog.get(product_id)

    def list_all(self):
        return self.catalog.list_all()

    def list_by_category(self, category):
        return self.catalog.list_by_category(category)

    def list_by_owner(self, owner):
        return self.catalog.list_by_owner(owner)
