from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, Any
from uuid import uuid4


@dataclass
class ExecutionObject:
    """
    Enterprise Execution Object

    Represents an execution generated
    from a planning object.
    """

    plan_id: str

    step_number: int

    action: str

    capability_code: str

    input_data: Dict[str, Any] = field(default_factory=dict)

    output_data: Dict[str, Any] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "EXECUTION"

    execution_id: str = field(default_factory=lambda: str(uuid4()))

    status: str = "PENDING"

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self):
        return self.__dict__
