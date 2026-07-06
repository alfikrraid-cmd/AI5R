class WorkflowRuntime:

    def start(self, workflow):

        workflow.status = "RUNNING"

        return workflow

    def finish(self, workflow):

        workflow.status = "COMPLETED"

        return workflow
