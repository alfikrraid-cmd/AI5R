from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass
class Capability:

    capability_id: str
    name: str
    description: str
    created_at: str = datetime.now(UTC).isoformat()



class CapabilityRegistry:


    def __init__(self):

        self.capabilities = {}



    def register(
        self,
        capability: Capability
    ):

        self.capabilities[
            capability.capability_id
        ] = capability


        return {

            "status":"REGISTERED",

            "capability_id":
            capability.capability_id

        }



    def get(
        self,
        capability_id: str
    ):

        return self.capabilities.get(
            capability_id
        )



    def list_all(self):

        return list(
            self.capabilities.values()
        )
