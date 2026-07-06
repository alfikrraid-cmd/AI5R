class WorkflowGraph:

    def ready_steps(self, workflow):

        completed = {
            step.step_id
            for step in workflow.steps
            if step.status == "COMPLETED"
        }

        ready = []

        for step in workflow.steps:
            if step.status != "PENDING":
                continue

            if all(dependency in completed for dependency in step.depends_on):
                ready.append(step)

        return ready

    def complete_step(self, step):

        step.status = "COMPLETED"

        return step
