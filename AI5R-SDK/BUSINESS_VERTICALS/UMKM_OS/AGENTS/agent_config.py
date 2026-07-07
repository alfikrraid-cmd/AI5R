from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class UMKMAgentConfig:

    agent_id: str
    role: str
    goal: str
    knowledge_domain: str
    workflow: str
    created_at: str = datetime.now(UTC).isoformat()



class UMKMAgentRegistry:


    def __init__(self):

        self.agents = {}



    def register(
        self,
        agent: UMKMAgentConfig
    ):

        self.agents[
            agent.agent_id
        ] = agent


        return {

            "status":"REGISTERED",

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
