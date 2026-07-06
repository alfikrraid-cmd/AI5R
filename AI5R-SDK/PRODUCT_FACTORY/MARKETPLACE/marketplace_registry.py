from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class MarketplaceProduct:

    product_id: str
    name: str
    domain: str
    version: str
    status: str = "ACTIVE"
    created_at: str = datetime.now(UTC).isoformat()



class MarketplaceRegistry:


    def __init__(self):

        self.products = {}



    def publish(
        self,
        product: MarketplaceProduct
    ):

        self.products[
            product.product_id
        ] = product


        return {

            "status":"PUBLISHED",

            "product_id":
            product.product_id

        }



    def get(
        self,
        product_id: str
    ):

        return self.products.get(
            product_id
        )



    def list_products(self):

        return list(
            self.products.values()
        )
