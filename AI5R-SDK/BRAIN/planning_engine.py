from uuid import uuid4

from .enterprise_cognitive_station import EnterpriseCognitiveStation
from .planning_object import PlanningObject


class PlanningEngine(EnterpriseCognitiveStation):

    input_object_type = "decision"

    output_object_type = "plan"

    def transform(self, decision):

        hypothesis = decision.selected_hypothesis

        actions = [
            {
                "step": 1,
                "title": "Validate selected hypothesis",
                "description": hypothesis["description"],
            },
            {
                "step": 2,
                "title": "Collect additional enterprise evidence",
                "description": "Verify assumptions before execution.",
            },
            {
                "step": 3,
                "title": "Prepare execution resources",
                "description": "Allocate enterprise resources.",
            },
        ]

        return PlanningObject(

            plan_id=f"plan-{uuid4()}",

            decision_id=decision.decision_id,

            actions=actions,

            priority="high"
            if decision.confidence >= 0.8
            else "normal",

            estimated_steps=len(actions),

            digital_thread_id=decision.digital_thread_id,

            enterprise_context={
                "stage": "planning",
                "derived_from": "decision",
            },
        )
