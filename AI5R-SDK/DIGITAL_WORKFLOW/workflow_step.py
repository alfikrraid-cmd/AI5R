from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class WorkflowStep:
    title: str
    assigned_role: str

    step_id: str = field(default_factory=lambda: str(uuid4()))

    status: str = "PENDING"

    depends_on: list[str] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
