from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutiveGoal:
    goal_id: str
    description: str
    target_value: float
    period: str = "monthly"
    currency: str = "IDR"
    metadata: dict[str, Any] = field(default_factory=dict)
