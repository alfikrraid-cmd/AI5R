from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _now():
    return datetime.now(UTC).isoformat()


@dataclass
class ExecutionResult:
    status: str
    production_plan: dict
    artifacts: list
    workspace: dict
    reports: list
    metadata: dict[str, Any] = field(default_factory=dict)

    execution_id: str = field(
        default_factory=lambda: f"EXEC-{uuid4()}"
    )

    executed_at: str = field(default_factory=_now)
