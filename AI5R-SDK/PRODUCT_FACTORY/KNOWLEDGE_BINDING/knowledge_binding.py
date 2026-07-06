from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass
class KnowledgeBinding:

    product_id: str
    capability_id: str
    knowledge_domain: str
    created_at: str = datetime.now(UTC).isoformat()



class KnowledgeBindingRegistry:


    def __init__(self):

        self.bindings = []



    def bind(
        self,
        binding: KnowledgeBinding
    ):

        self.bindings.append(
            binding
        )


        return {

            "status":"BOUND",

            "product_id":
            binding.product_id

        }



    def find_by_product(
        self,
        product_id: str
    ):

        return [

            item

            for item in self.bindings

            if item.product_id == product_id

        ]
