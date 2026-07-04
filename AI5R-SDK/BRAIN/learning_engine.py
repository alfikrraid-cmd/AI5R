from uuid import uuid4

from .enterprise_cognitive_station import EnterpriseCognitiveStation
from .learning_object import LearningObject


class LearningEngine(EnterpriseCognitiveStation):

    input_object_type = "outcome"

    output_object_type = "learning"

    def transform(self, outcome):

        if outcome.success:

            lesson = (
                "Execution completed successfully. "
                "Current enterprise reasoning is reinforced."
            )

            delta = 0.10

            knowledge_update = False

        else:

            lesson = (
                "Execution did not achieve expected outcome. "
                "Enterprise knowledge should be reviewed."
            )

            delta = -0.15

            knowledge_update = True

        return LearningObject(

            learning_id=f"learning-{uuid4()}",

            outcome_id=outcome.outcome_id,

            lesson=lesson,

            confidence_delta=delta,

            knowledge_update_required=knowledge_update,

            digital_thread_id=outcome.digital_thread_id,

            enterprise_context={

                "stage": "learning",

                "derived_from": "outcome",

            },
        )
