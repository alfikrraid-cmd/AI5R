from typing import Any

from REALTIME_ENGINE.DECISION_LOOP import (
    RealtimeDecisionLoop,
)

from REALTIME_ENGINE.BRAIN_CONNECTOR import (
    RealtimeBrainConnector,
)

from REALTIME_ENGINE.FEEDBACK_LOOP import (
    CognitiveFeedbackLoop,
)


class RealtimeOrchestrator:

    def __init__(self):

        self.decision_loop = RealtimeDecisionLoop()

        self.brain_connector = RealtimeBrainConnector()

        self.feedback_loop = CognitiveFeedbackLoop()


    def process(
        self,
        event: dict[str, Any]
    ):

        observation = {
            "event": event,
            "status": "OBSERVED"
        }


        brain_result = self.brain_connector.send_to_brain(
            observation
        )


        action_result = self.decision_loop.run(
            event
        )


        self.feedback_loop.record(
            action_result["action"],
            action_result
        )


        return {
            "status": "COMPLETED",
            "brain": brain_result["status"],
            "action": action_result["status"]
        }
