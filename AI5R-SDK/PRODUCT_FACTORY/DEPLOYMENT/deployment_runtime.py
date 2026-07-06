from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class ProductInstance:

    product_id: str
    version: str
    status: str
    created_at: str = datetime.now(UTC).isoformat()



class DeploymentRuntime:


    def __init__(self):

        self.instances = {}



    def deploy(
        self,
        product_id: str,
        version: str
    ):

        instance = ProductInstance(

            product_id=product_id,

            version=version,

            status="ACTIVE"

        )


        self.instances[
            product_id
        ] = instance


        return {

            "status":"DEPLOYED",

            "product_id":
            product_id

        }



    def status(
        self,
        product_id: str
    ):

        instance = self.instances.get(
            product_id
        )


        if not instance:

            return "NOT_FOUND"


        return instance.status
