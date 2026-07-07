from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class KnowledgeDomain:

    domain_id: str
    name: str
    topics: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class UMKMKnowledgeRegistry:


    def __init__(self):

        self.domains = {}



    def register(
        self,
        domain: KnowledgeDomain
    ):

        self.domains[
            domain.domain_id
        ] = domain


        return {

            "status":"REGISTERED",

            "domain_id":
            domain.domain_id

        }



    def get(
        self,
        domain_id: str
    ):

        return self.domains.get(
            domain_id
        )
