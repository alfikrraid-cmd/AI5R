from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class WorkflowStep:

    step_id: str
    agent_id: str
    action: str



@dataclass
class UMKMWorkflow:

    workflow_id: str
    name: str
    steps: list[WorkflowStep]
    created_at: str = datetime.now(UTC).isoformat()



class UMKMWorkflowEngine:


    def __init__(self):

        self.workflows = {}



    def create(
        self,
        workflow: UMKMWorkflow
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
