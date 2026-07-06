from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class WorkflowStep:

    step_id: str
    agent_id: str
    action: str



@dataclass
class ProductWorkflow:

    workflow_id: str
    product_id: str
    steps: list[WorkflowStep]
    created_at: str = datetime.now(UTC).isoformat()



class WorkflowFactory:


    def __init__(self):

        self.workflows = {}



    def create(
        self,
        workflow: ProductWorkflow
    ):

        self.workflows[
            workflow.workflow_id
        ] = workflow


        return {

            "status":"CREATED",

            "workflow_id":
            workflow.workflow_id

        }



    def get(
        self,
        workflow_id: str
    ):

        return self.workflows.get(
            workflow_id
        )
