from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class AuditWorkflow:

    workflow_id: str
    name: str
    steps: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class AuditWorkflowEngine:


    def __init__(self):

        self.workflows = {}



    def create(
        self,
        workflow: AuditWorkflow
    ):

        self.workflows[
            workflow.workflow_id
        ] = workflow


        return {

            "status":"CREATED",

            "workflow_id":
            workflow.workflow_id

        }



    def execute(
        self,
        workflow_id: str
    ):


        workflow = self.workflows.get(
            workflow_id
        )


        if not workflow:

            return {

                "status":"NOT_FOUND"

            }


        return {

            "status":"EXECUTED",

            "steps":
            len(workflow.steps)

        }
