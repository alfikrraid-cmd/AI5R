from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class ExecutionObject:
    plan_id: str
    step_number: int
    action: str
    capability_code: str
    input_data: dict[str, Any]
    capability_id: str = "CAPABILITY-DEFAULT"
    object_type: str = "EXECUTION"
    status: str = "PENDING"
    output_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_id: str = field(default_factory=lambda: f"EXEC-{uuid4()}")
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
