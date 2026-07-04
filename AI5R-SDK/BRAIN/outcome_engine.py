from uuid import uuid4

from .enterprise_cognitive_station import EnterpriseCognitiveStation
from .outcome_object import OutcomeObject


class OutcomeEngine(EnterpriseCognitiveStation):

    input_object_type = "execution"

    output_object_type = "outcome"

    def transform(self, execution):

        completed = []

        for task in execution.tasks:

            completed.append({
                **task,
                "status": "completed",
            })

        completion_rate = (
            len(completed) / len(execution.tasks)
            if execution.tasks
            else 0.0
        )

        return OutcomeObject(

            outcome_id=f"outcome-{uuid4()}",

            execution_id=execution.execution_id,

            completed_tasks=completed,

            success=(completion_rate == 1.0),

            completion_rate=completion_rate,

            digital_thread_id=execution.digital_thread_id,

            enterprise_context={
                "stage": "outcome",
                "derived_from": "execution",
                "completed_tasks": len(completed),
            },
        )
