from typing import Any


class AgentRuntimeBridge:

    def __init__(self):
        self.agents = {}


    def register_agent(
        self,
        agent_id: str,
        agent
    ):

        self.agents[agent_id] = agent

        return {
            "status": "REGISTERED",
            "agent_id": agent_id
        }


    def dispatch(
        self,
        agent_id: str,
        task: dict[str, Any]
    ):

        agent = self.agents.get(agent_id)

        if not agent:
            return {
                "status": "AGENT_NOT_FOUND"
            }


        result = agent.execute(task)


        return {
            "status": "EXECUTED",
            "agent_id": agent_id,
            "result": result
        }
