from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import List, Dict, Any
from uuid import uuid4


@dataclass
class PlanningObject:
    """
    Enterprise Planning Object

    Represents an executable plan generated
    from a mission.
    """

    mission_id: str

    goal: str

    required_capabilities: List[str] = field(default_factory=list)

    execution_steps: List[Dict[str, Any]] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "PLAN"

    plan_id: str = field(default_factory=lambda: str(uuid4()))

    status: str = "PLANNED"

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self):
        return self.__dict__
