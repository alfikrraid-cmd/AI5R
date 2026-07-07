from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class SchoolVertical:

    vertical_id: str
    name: str
    domain: str
    agents: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class SchoolRuntime:


    def __init__(self):

        self.verticals = {}



    def register(
        self,
        vertical: SchoolVertical
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
