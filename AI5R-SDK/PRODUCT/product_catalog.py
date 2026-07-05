class ProductCatalog:

    def __init__(self):
        self._products = {}

    def register(self, product_result):

        product = product_result["product"]

        self._products[product.product_id] = product_result

        return {
            "status": "REGISTERED",
            "product_id": product.product_id,
        }

    def get(self, product_id):
        return self._products.get(product_id)

    def list_all(self):
        return list(self._products.values())

    def list_by_category(self, category):
        return [
            x
            for x in self._products.values()
            if x["product"].category == category
        ]

    def list_by_owner(self, owner):
        return [
            x
            for x in self._products.values()
            if x["product"].owner == owner
        ]
