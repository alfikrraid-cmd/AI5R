from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class DecisionResult:
    decision: str
    action: str
    created_at: str = datetime.now(UTC).isoformat()


class RealtimeDecisionLoop:

    def __init__(self):
        self.history = []


    def observe(
        self,
        event: dict[str, Any]
    ):

        return {
            "observation": event,
            "status": "OBSERVED"
        }


    def decide(
        self,
        observation: dict[str, Any]
    ):

        return DecisionResult(
            decision="PROCESS_EVENT",
            action="EXECUTE_RESPONSE"
        )


    def execute(
        self,
        decision: DecisionResult
    ):

        result = {
            "status": "EXECUTED",
            "decision": decision.decision,
            "action": decision.action
        }

        self.history.append(result)

        return result


    def run(
        self,
        event: dict[str, Any]
    ):

        observation = self.observe(event)

        decision = self.decide(observation)

        return self.execute(decision)
