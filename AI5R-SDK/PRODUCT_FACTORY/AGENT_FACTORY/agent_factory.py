from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class ProductAgent:

    agent_id: str
    product_id: str
    role: str
    created_at: str = datetime.now(UTC).isoformat()



class AgentFactory:


    def __init__(self):

        self.agents = {}



    def create(
        self,
        agent: ProductAgent
    ):

        self.agents[
            agent.agent_id
        ] = agent


        return {

            "status":"CREATED",

            "agent_id":
            agent.agent_id

        }



    def get(
        self,
        agent_id: str
    ):

        return self.agents.get(
            agent_id
        )



    def list_product_agents(
        self,
        product_id: str
    ):

        return [

            agent

            for agent in self.agents.values()

            if agent.product_id == product_id

        ]
