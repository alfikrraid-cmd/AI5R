from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ExecutionResult:
    employee_id: str
    employee_name: str
    task_id: str
    task_title: str
    status: str
    output: dict
    observation: dict = field(default_factory=dict)
    learning: dict = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
