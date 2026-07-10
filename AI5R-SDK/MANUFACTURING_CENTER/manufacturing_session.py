from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from MANUFACTURING.ORDERS import ManufacturingOrder

from .manufacturing_context import ManufacturingContext
from .manufacturing_result import ManufacturingResult
from .manufacturing_status import ManufacturingStatus


@dataclass(slots=True, kw_only=True)
class ManufacturingSession:
    session_id: str
    order: ManufacturingOrder
    context: ManufacturingContext
    status: ManufacturingStatus = ManufacturingStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    current_stage: str | None = None
    progress: int = 0
    status_history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.session_id = self.session_id.strip()

        if not self.session_id:
            raise ValueError("session_id must not be empty")

        if not self.order.validate():
            raise ValueError("manufacturing order is invalid")

        if self.context.manufacturing_id != self.session_id:
            raise ValueError(
                "context.manufacturing_id must equal session_id"
            )

        self._validate_progress(self.progress)

        if self.started_at is not None and self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")

        if self.finished_at is not None and self.finished_at.tzinfo is None:
            raise ValueError("finished_at must be timezone-aware")

        if self.finished_at is not None and self.started_at is None:
            raise ValueError("finished_at requires started_at")

        self.current_stage = self._clean_optional_stage(self.current_stage)
        self.status_history = [
            dict(entry) for entry in self.status_history
        ]
        self.metadata = dict(self.metadata)

    @staticmethod
    def _validate_progress(progress: int) -> None:
        if isinstance(progress, bool) or not isinstance(progress, int):
            raise TypeError("progress must be an integer")

        if not 0 <= progress <= 100:
            raise ValueError("progress must be between 0 and 100")

    @staticmethod
    def _clean_reason(reason: str) -> str:
        cleaned_reason = reason.strip()

        if not cleaned_reason:
            raise ValueError("reason must not be empty")

        return cleaned_reason

    @staticmethod
    def _clean_optional_stage(stage: str | None) -> str | None:
        if stage is None:
            return None

        cleaned_stage = stage.strip()

        if not cleaned_stage:
            raise ValueError("stage must not be empty")

        return cleaned_stage

    def _ensure_not_terminal(self, action: str) -> None:
        if self.is_terminal:
            raise RuntimeError(
                f"cannot {action} a terminal manufacturing session"
            )

    def _record_history(
        self,
        *,
        status: ManufacturingStatus,
        stage: str | None,
        progress: int,
        details: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        event_timestamp = timestamp or datetime.now(UTC)

        self.status_history.append(
            {
                "status": status,
                "timestamp": event_timestamp,
                "stage": stage,
                "progress": progress,
                "details": dict(details or {}),
            }
        )

    def start(self) -> None:
        if self.status is not ManufacturingStatus.PENDING:
            raise RuntimeError(
                "start is only allowed from pending status"
            )

        now = datetime.now(UTC)
        self.status = ManufacturingStatus.VALIDATING
        self.started_at = now

        self._record_history(
            status=self.status,
            stage=self.current_stage,
            progress=self.progress,
            timestamp=now,
        )

    def transition(
        self,
        status: ManufacturingStatus,
        *,
        stage: str | None = None,
        progress: int | None = None,
    ) -> None:
        self._ensure_not_terminal("transition")

        if not self.is_started:
            raise RuntimeError(
                "manufacturing session must be started before transition"
            )

        if status.is_terminal:
            raise ValueError(
                "use complete, fail, or cancel for terminal transitions"
            )

        if status is ManufacturingStatus.PENDING:
            raise ValueError("cannot transition back to pending")

        cleaned_stage = self._clean_optional_stage(stage)

        if progress is not None:
            self._validate_progress(progress)

        self.status = status

        if cleaned_stage is not None:
            self.current_stage = cleaned_stage

        if progress is not None:
            self.progress = progress

        self._record_history(
            status=self.status,
            stage=self.current_stage,
            progress=self.progress,
        )

    def complete(self) -> ManufacturingResult:
        self._ensure_not_terminal("complete")

        now = datetime.now(UTC)
        self._ensure_started_at(now)

        self.status = ManufacturingStatus.COMPLETED
        self.progress = 100
        self.finished_at = now

        self._record_history(
            status=self.status,
            stage=self.current_stage,
            progress=self.progress,
            timestamp=now,
        )

        return self._build_result()

    def fail(self, reason: str) -> ManufacturingResult:
        self._ensure_not_terminal("fail")
        cleaned_reason = self._clean_reason(reason)

        now = datetime.now(UTC)
        self._ensure_started_at(now)

        self.status = ManufacturingStatus.FAILED
        self.finished_at = now

        self._record_history(
            status=self.status,
            stage=self.current_stage,
            progress=self.progress,
            details={"reason": cleaned_reason},
            timestamp=now,
        )

        result = self._build_result()
        result.add_log(f"Manufacturing failed: {cleaned_reason}")
        return result

    def cancel(self, reason: str) -> ManufacturingResult:
        self._ensure_not_terminal("cancel")
        cleaned_reason = self._clean_reason(reason)

        now = datetime.now(UTC)
        self._ensure_started_at(now)

        self.status = ManufacturingStatus.CANCELLED
        self.finished_at = now

        self._record_history(
            status=self.status,
            stage=self.current_stage,
            progress=self.progress,
            details={"reason": cleaned_reason},
            timestamp=now,
        )

        result = self._build_result()
        result.add_log(f"Manufacturing cancelled: {cleaned_reason}")
        return result

    def _ensure_started_at(self, timestamp: datetime) -> None:
        if self.started_at is None:
            self.started_at = timestamp

    def _build_result(self) -> ManufacturingResult:
        if self.started_at is None:
            raise RuntimeError(
                "started_at is required to build manufacturing result"
            )

        result = ManufacturingResult(
            manufacturing_id=self.session_id,
            status=self.status,
            started_at=self.started_at,
            finished_at=self.finished_at,
            duration=self.duration,
            metadata=dict(self.metadata),
        )

        for entry in self.status_history:
            result.add_event(dict(entry))

        return result

    @property
    def is_started(self) -> bool:
        return self.started_at is not None

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    @property
    def duration(self) -> float | None:
        if self.started_at is None:
            return None

        end = self.finished_at or datetime.now(UTC)
        duration = (end - self.started_at).total_seconds()

        if duration < 0:
            raise ValueError("duration can never be negative")

        return duration
