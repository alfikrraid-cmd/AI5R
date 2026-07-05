from PRODUCT.product_object import ProductObject


class ProductEngine:

    def build(
        self,
        product: ProductObject,
    ):

        return {
            "status": "READY",
            "product": product,
            "profile": {
                "product_code": product.product_code,
                "product_name": product.product_name,
                "category": product.category,
                "version": product.version,
                "description": product.description,
                "owner": product.owner,
                "runtime": product.runtime,
            },
        }
