from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .manufacturing_status import ManufacturingStatus


@dataclass(slots=True, kw_only=True)
class ManufacturingStep:
    step_id: str
    capability_id: str
    name: str
    status: ManufacturingStatus = ManufacturingStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.step_id = self.step_id.strip()
        self.capability_id = self.capability_id.strip()
        self.name = self.name.strip()

        if not self.step_id:
            raise ValueError("step_id must not be empty")
        if not self.capability_id:
            raise ValueError("capability_id must not be empty")
        if not self.name:
            raise ValueError("name must not be empty")

        if self.started_at is not None and self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")

        if self.finished_at is not None and self.finished_at.tzinfo is None:
            raise ValueError("finished_at must be timezone-aware")

        if self.finished_at is not None and self.started_at is None:
            raise ValueError("finished_at requires started_at")

        if (
            self.started_at is not None
            and self.finished_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError(
                "finished_at must not be earlier than started_at"
            )

        self.inputs = dict(self.inputs)
        self.outputs = dict(self.outputs)
        self.metadata = dict(self.metadata)

    def _ensure_pending(self) -> None:
        if self.status is not ManufacturingStatus.PENDING:
            raise RuntimeError(
                "manufacturing step can only start from pending status"
            )

    def _ensure_running(self) -> None:
        if self.status is not ManufacturingStatus.MANUFACTURING:
            raise RuntimeError(
                "manufacturing step must be running"
            )

    def start(self) -> None:
        self._ensure_pending()

        self.status = ManufacturingStatus.MANUFACTURING
        self.started_at = datetime.now(UTC)

    def complete(self, outputs: dict[str, Any]) -> None:
        self._ensure_running()

        self.status = ManufacturingStatus.COMPLETED
        self.finished_at = datetime.now(UTC)
        self.outputs = dict(outputs)

    def fail(self, reason: str) -> None:
        self._ensure_running()

        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise ValueError("reason must not be empty")

        self.status = ManufacturingStatus.FAILED
        self.finished_at = datetime.now(UTC)
        self.metadata["reason"] = cleaned_reason

    def cancel(self, reason: str) -> None:
        self._ensure_running()

        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise ValueError("reason must not be empty")

        self.status = ManufacturingStatus.CANCELLED
        self.finished_at = datetime.now(UTC)
        self.metadata["reason"] = cleaned_reason

    @property
    def duration(self) -> float | None:
        if self.started_at is None:
            return None

        end = self.finished_at or datetime.now(UTC)
        duration = (end - self.started_at).total_seconds()

        if duration < 0:
            raise ValueError("duration can never be negative")

        return duration

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal
