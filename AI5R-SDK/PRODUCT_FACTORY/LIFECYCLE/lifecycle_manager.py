from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class ProductLifecycle:

    product_id: str
    version: str
    state: str
    created_at: str = datetime.now(UTC).isoformat()



class LifecycleManager:


    def __init__(self):

        self.products = {}



    def create(
        self,
        product_id: str,
        version: str
    ):

        product = ProductLifecycle(

            product_id=product_id,

            version=version,

            state="CREATED"

        )


        self.products[
            product_id
        ] = product


        return product



    def transition(
        self,
        product_id: str,
        state: str
    ):

        product = self.products.get(
            product_id
        )


        if product:

            product.state = state


        return product.state



    def get(
        self,
        product_id: str
    ):

        return self.products.get(
            product_id
        )
