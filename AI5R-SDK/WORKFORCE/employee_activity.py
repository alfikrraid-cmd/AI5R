from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class EmployeeActivity:
    employee_id: str
    activity_type: str
    status: str
    message: str
    progress: int = 0
    work_item_id: str | None = None
    sprint_id: str | None = None
    mission_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    activity_id: str = field(default_factory=lambda: f"ACT-{uuid4()}")
    started_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def update(
        self,
        status: str,
        message: str,
        progress: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.status = status
        self.message = message

        if progress is not None:
            if progress < 0 or progress > 100:
                raise ValueError("progress must be between 0 and 100")
            self.progress = progress

        if metadata:
            self.metadata.update(metadata)

        self.updated_at = _now()
