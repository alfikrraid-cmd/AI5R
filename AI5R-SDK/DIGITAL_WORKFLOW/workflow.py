from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from .workflow_step import WorkflowStep


@dataclass
class Workflow:

    title: str

    description: str = ""

    workflow_id: str = field(default_factory=lambda: str(uuid4()))

    status: str = "CREATED"

    steps: list[WorkflowStep] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_step(self, step: WorkflowStep):

        self.steps.append(step)

        return step

    def step_count(self):

        return len(self.steps)
