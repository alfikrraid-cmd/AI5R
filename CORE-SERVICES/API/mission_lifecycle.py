from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

# Default bounds
DEFAULT_MAX_REVISION_ITERATIONS: int = 3
MAX_REVISION_ITERATIONS: int = 3


def _now() -> str:
    return datetime.now(UTC).isoformat()


class MissionStatus:
    """Canonical Level 6 Mission Lifecycle States."""
    DRAFT = "DRAFT"
    PLANNING = "PLANNING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    REVIEWING = "REVIEWING"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    REVISING = "REVISING"
    RE_REVIEWING = "RE_REVIEWING"
    READY_FOR_CHIEF_APPROVAL = "READY_FOR_CHIEF_APPROVAL"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"

    # Terminal / Failure paths
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    REVISION_LIMIT_REACHED = "REVISION_LIMIT_REACHED"
    CANCELLED = "CANCELLED"

    @classmethod
    def is_active(cls, status: str) -> bool:
        return status in (
            cls.PLANNING,
            cls.READY,
            cls.EXECUTING,
            cls.REVIEWING,
            cls.REVISION_REQUIRED,
            cls.REVISING,
            cls.RE_REVIEWING,
        )

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status in (
            cls.COMPLETED,
            cls.APPROVED,
            cls.BLOCKED,
            cls.FAILED,
            cls.REVISION_LIMIT_REACHED,
            cls.CANCELLED,
        )


class LoopSafetyError(Exception):
    """Base exception for pathological loop detection and safety guard triggers."""
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}


class RepeatedFindingError(LoopSafetyError):
    """Raised when consecutive review iterations yield identical findings without change."""
    pass


class RepeatedPatchError(LoopSafetyError):
    """Raised when consecutive revisions produce identical patches or unchanged diffs."""
    pass


class DependencyDeadlockError(LoopSafetyError):
    """Raised when task dependency graph is deadlocked and no eligible task can progress."""
    pass


class MissingEmployeeError(LoopSafetyError):
    """Raised when a task cannot execute because the required digital employee is missing."""
    pass


class SandboxExecutionError(LoopSafetyError):
    """Raised when the controlled coding sandbox fails or violates path security bounds."""
    pass


class ExecutionTimeoutError(LoopSafetyError):
    """Raised when an execution or review step exceeds the maximum allowed time budget."""
    pass


@dataclass
class ReviewFinding:
    """Structured review finding produced by QA (SENTRY) or Security (AIGIS)."""
    finding_id: str
    severity: str          # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    category: str          # "TEST_FAILURE" | "SECURITY_VULNERABILITY" | "REGRESSION" | "FUNCTIONAL_BUG" | "COMPLIANCE"
    description: str
    evidence: str
    affected_task_id: str
    responsible_employee_id: str
    responsible_role: str
    required_action: str
    status: str = "OPEN"   # "OPEN" | "RESOLVED" | "WONTFIX"
    created_at: str = field(default_factory=_now)
    resolved_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "evidence": self.evidence,
            "affected_task_id": self.affected_task_id,
            "responsible_employee_id": self.responsible_employee_id,
            "responsible_role": self.responsible_role,
            "required_action": self.required_action,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "metadata": self.metadata,
        }

