from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass
class ProductPackage:

    product_id: str
    manifest: dict
    agents: list[str]
    capabilities: list[str]
    workflow_id: str
    version: str
    created_at: str = datetime.now(UTC).isoformat()



class ProductPackager:


    def __init__(self):

        self.packages = {}



    def package(
        self,
        product: ProductPackage
    ):

        self.packages[
            product.product_id
        ] = product


        return {

            "status":"PACKAGED",

            "product_id":
            product.product_id,

            "version":
            product.version

        }



    def release_ready(
        self,
        product_id: str
    ):

        product = self.packages.get(
            product_id
        )


        if not product:

            return False


        return all([

            product.manifest,

            product.agents,

            product.capabilities,

            product.workflow_id

        ])
