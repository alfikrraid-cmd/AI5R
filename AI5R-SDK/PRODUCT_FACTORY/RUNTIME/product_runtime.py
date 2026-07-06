from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class AIProductManifest:

    product_id: str
    name: str
    domain: str
    capabilities: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class ProductRuntime:


    def __init__(self):

        self.products = {}



    def register(
        self,
        manifest: AIProductManifest
    ):

        self.products[
            manifest.product_id
        ] = manifest


        return {

            "status":"REGISTERED",

            "product_id":
            manifest.product_id

        }



    def get_product(
        self,
        product_id: str
    ):

        return self.products.get(
            product_id
        )
