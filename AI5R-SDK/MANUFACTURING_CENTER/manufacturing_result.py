from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .manufacturing_status import ManufacturingStatus


@dataclass(slots=True, kw_only=True)
class ManufacturingResult:
    manufacturing_id: str
    status: ManufacturingStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration: float | None = None
    artifacts: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    release: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.manufacturing_id.strip():
            raise ValueError("manufacturing_id is required")

        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")

        if self.finished_at is not None and self.finished_at.tzinfo is None:
            raise ValueError("finished_at must be timezone-aware")

        if self.duration is not None and self.duration < 0:
            raise ValueError("duration can never be negative")

    def _calculate_duration(self) -> float:
        if self.finished_at is None:
            raise RuntimeError("finished_at is required to calculate duration")

        duration = (self.finished_at - self.started_at).total_seconds()

        if duration < 0:
            raise ValueError("duration can never be negative")

        return duration

    def _ensure_active(self) -> None:
        if self.status.is_terminal:
            raise RuntimeError(
                f"Manufacturing result is already terminal: {self.status}"
            )

    def complete(self) -> None:
        self._ensure_active()
        self.finished_at = datetime.now(UTC)
        self.duration = self._calculate_duration()
        self.status = ManufacturingStatus.COMPLETED

    def fail(self, reason: str) -> None:
        self._ensure_active()

        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise ValueError("failure reason is required")

        self.finished_at = datetime.now(UTC)
        self.duration = self._calculate_duration()
        self.status = ManufacturingStatus.FAILED
        self.add_log(f"Manufacturing failed: {cleaned_reason}")

    def add_event(self, event: dict[str, Any]) -> None:
        self.events.append(dict(event))

    def add_log(self, message: str) -> None:
        cleaned_message = message.strip()
        if not cleaned_message:
            raise ValueError("log message is required")

        self.logs.append(cleaned_message)

    def add_artifact(self, path: str) -> None:
        cleaned_path = path.strip()
        if not cleaned_path:
            raise ValueError("artifact path is required")

        self.artifacts.append(cleaned_path)

    @property
    def is_completed(self) -> bool:
        return self.status is ManufacturingStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status is ManufacturingStatus.FAILED

    @property
    def is_running(self) -> bool:
        return self.status.is_active
