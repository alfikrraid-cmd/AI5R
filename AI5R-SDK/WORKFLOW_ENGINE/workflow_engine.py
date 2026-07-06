from dataclasses import dataclass, field


DEFAULT_PIPELINE = [
    "Specification",
    "Factory",
    "Assembly",
    "Artifact",
    "Registry",
    "Runtime",
]


@dataclass
class ManufacturingWorkflow:
    workflow_name: str
    stations: list[str] = field(default_factory=lambda: DEFAULT_PIPELINE.copy())

    def validate(self):
        if not self.workflow_name:
            raise ValueError("workflow_name is required")

        if not self.stations:
            raise ValueError("stations are required")

        return {
            "status": "VALID",
            "workflow": self.workflow_name,
            "stations": self.stations,
        }


class WorkflowEngine:
    def __init__(self):
        self._workflows = {}

    def register(self, workflow: ManufacturingWorkflow):
        definition = workflow.validate()

        self._workflows[definition["workflow"]] = definition

        return {
            "status": "REGISTERED",
            "workflow": definition["workflow"],
            "stations": definition["stations"],
        }

    def get(self, workflow_name: str):
        return self._workflows.get(workflow_name)

    def execute(self, workflow_name: str):
        workflow = self.get(workflow_name)

        if workflow is None:
            return {
                "status": "NOT_FOUND",
                "workflow": workflow_name,
            }

        executed = []

        for station in workflow["stations"]:
            executed.append({
                "station": station,
                "status": "COMPLETED",
            })

        return {
            "status": "COMPLETED",
            "workflow": workflow_name,
            "stations": executed,
        }
