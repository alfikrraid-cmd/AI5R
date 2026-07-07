from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class CustomerWorkspace:

    customer_id: str
    system_name: str
    url: str
    modules: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class WorkspaceGenerator:


    def create(
        self,
        customer_id: str,
        system_name: str,
        modules: list[str]
    ):


        return CustomerWorkspace(

            customer_id=
            customer_id,

            system_name=
            system_name,

            url=
            f"{customer_id}.osa-system.com",

            modules=
            modules

        )
