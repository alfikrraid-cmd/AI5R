from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class BusinessVertical:

    vertical_id: str
    name: str
    domain: str
    agents: list[str]
    capabilities: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class VerticalRuntime:


    def __init__(self):

        self.verticals = {}



    def register(
        self,
        vertical: BusinessVertical
    ):

        self.verticals[
            vertical.vertical_id
        ] = vertical


        return {

            "status":"REGISTERED",

            "vertical_id":
            vertical.vertical_id

        }



    def get(
        self,
        vertical_id: str
    ):

        return self.verticals.get(
            vertical_id
        )



    def list_all(self):

        return list(
            self.verticals.values()
        )
