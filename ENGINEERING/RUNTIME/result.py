from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CapabilityStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class CapabilityResult:
    status: CapabilityStatus
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration: float = 0.0

    @classmethod
    def success(
        cls,
        message: str = "",
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> "CapabilityResult":
        return cls._build(
            status=CapabilityStatus.SUCCESS,
            message=message,
            payload=payload,
            metadata=metadata,
            started_at=started_at,
            finished_at=finished_at,
        )

    @classmethod
    def failure(
        cls,
        message: str = "",
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> "CapabilityResult":
        return cls._build(
            status=CapabilityStatus.FAILED,
            message=message,
            payload=payload,
            metadata=metadata,
            started_at=started_at,
            finished_at=finished_at,
        )

    @classmethod
    def _build(
        cls,
        status: CapabilityStatus,
        message: str,
        payload: dict[str, Any] | None,
        metadata: dict[str, Any] | None,
        started_at: datetime | None,
        finished_at: datetime | None,
    ) -> "CapabilityResult":
        started_at = started_at or datetime.now(timezone.utc)
        finished_at = finished_at or datetime.now(timezone.utc)

        return cls(
            status=status,
            message=message,
            payload=payload or {},
            metadata=metadata or {},
            started_at=started_at,
            finished_at=finished_at,
            duration=(finished_at - started_at).total_seconds(),
        )
