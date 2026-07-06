from __future__ import annotations

from .agent_runtime import AgentRuntime


class MultiAgentRuntime:
    def __init__(self):
        self._agents: dict[str, AgentRuntime] = {}

    def register_agent(
        self,
        agent_id: str,
    ) -> AgentRuntime:

        if agent_id not in self._agents:
            self._agents[agent_id] = AgentRuntime(agent_id)

        return self._agents[agent_id]

    def get_agent(
        self,
        agent_id: str,
    ):
        return self._agents.get(agent_id)

    def require_agent(
        self,
        agent_id: str,
    ):
        agent = self.get_agent(agent_id)

        if agent is None:
            raise KeyError(f"Unknown agent: {agent_id}")

        return agent

    def start_agent(self, agent_id: str):
        agent = self.register_agent(agent_id)
        agent.start()
        return agent

    def stop_agent(self, agent_id: str):
        self.require_agent(agent_id).stop()

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
    ):
        self.require_agent(sender_id)
        receiver = self.register_agent(receiver_id)
        receiver.receive()

    def process_next(
        self,
        agent_id: str,
    ):
        self.require_agent(agent_id).consume()

    def list_agents(self):
        return list(self._agents.values())

    def snapshot(self):
        return {
            agent.agent_id: agent.snapshot()
            for agent in self._agents.values()
        }
