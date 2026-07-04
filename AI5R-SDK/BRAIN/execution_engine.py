from uuid import uuid4

from .enterprise_cognitive_station import EnterpriseCognitiveStation
from .execution_object import ExecutionObject


class ExecutionEngine(EnterpriseCognitiveStation):

    input_object_type = "planning"

    output_object_type = "execution"

    def transform(self, planning):

        tasks = []

        for action in planning.actions:

            tasks.append({

                "task_id": f"T-{action['step']}",

                "step": action["step"],

                "title": action["title"],

                "description": action["description"],

                "status": "pending",

            })

        return ExecutionObject(

            execution_id=f"execution-{uuid4()}",

            plan_id=planning.plan_id,

            tasks=tasks,

            progress=0.0,

            status="ready",

            digital_thread_id=planning.digital_thread_id,

            enterprise_context={

                "stage": "execution",

                "derived_from": "planning",

                "task_count": len(tasks),

            },
        )
