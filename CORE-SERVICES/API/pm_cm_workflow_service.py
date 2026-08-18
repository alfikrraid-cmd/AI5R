"""MWO-LTSA-PM-CM-INTAKE-001 -- the one workflow state machine shared by
PM Occurrence and Condition Monitoring Reading (Phase 10: "avoid state
explosion" -- both domains follow the exact same draft/submit/review
lifecycle, so this is one pure-logic module, not two).

Pure logic, zero DB I/O -- same "inject the repository, decide in pure
functions" discipline auth_admin_service.py/installation_review_service.py
already establish.

Vocabulary (from repository/business evidence, not invented):
  workflow_status: DRAFT -> SUBMITTED -> RETURNED_FOR_CORRECTION -> SUBMITTED
                    (loop) -> FINALIZED
  technical_outcome (set only when workflow_status becomes FINALIZED via
                    John Crane's own action): ACKNOWLEDGED | TECHNICALLY_APPROVED

A "return for correction" can come from either TAP_ADMIN (administrative
review, Phase 12) or JOHN_CRANE_ENGINEER (technical review, Phase 13) --
both reuse the same RETURNED_FOR_CORRECTION status; the caller records
which actor/comment column to populate (auth_review_service's
reviewed_by/reviewed_at/return_reason vs technical_reviewed_by/
technical_reviewed_at/technical_comment), this module only decides
whether the transition itself is legal.
"""

from __future__ import annotations

DRAFT = "DRAFT"
SUBMITTED = "SUBMITTED"
RETURNED_FOR_CORRECTION = "RETURNED_FOR_CORRECTION"
FINALIZED = "FINALIZED"

ACKNOWLEDGED = "ACKNOWLEDGED"
TECHNICALLY_APPROVED = "TECHNICALLY_APPROVED"
TECHNICAL_OUTCOMES = frozenset({ACKNOWLEDGED, TECHNICALLY_APPROVED})

# Phase 15: DRAFT and RETURNED_FOR_CORRECTION are editable; SUBMITTED
# restricts field editing (only a review/technical-review action may move
# it); FINALIZED must never be silently rewritten.
_EDITABLE_STATUSES = frozenset({DRAFT, RETURNED_FOR_CORRECTION})

_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    DRAFT: frozenset({SUBMITTED}),
    SUBMITTED: frozenset({RETURNED_FOR_CORRECTION, FINALIZED}),
    RETURNED_FOR_CORRECTION: frozenset({SUBMITTED}),
    FINALIZED: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a workflow_status transition is not in the allowed
    graph above -- e.g. submitting an already-FINALIZED record, or
    technically-reviewing a still-DRAFT one."""


class RecordNotEditableError(ValueError):
    """Raised when a field edit is attempted against a record whose
    workflow_status is not DRAFT/RETURNED_FOR_CORRECTION (Phase 15)."""


def is_editable(workflow_status: str) -> bool:
    return workflow_status in _EDITABLE_STATUSES


def guard_editable(workflow_status: str) -> None:
    if not is_editable(workflow_status):
        raise RecordNotEditableError(
            f"record is not editable in workflow_status={workflow_status!r} "
            "(only DRAFT/RETURNED_FOR_CORRECTION allow field edits)"
        )


def guard_transition(current_status: str, next_status: str) -> None:
    allowed = _ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if next_status not in allowed:
        raise InvalidTransitionError(
            f"cannot transition workflow_status from {current_status!r} to {next_status!r}"
        )


def submit(current_status: str) -> str:
    """DRAFT or RETURNED_FOR_CORRECTION -> SUBMITTED."""
    guard_transition(current_status, SUBMITTED)
    return SUBMITTED


def return_for_correction(current_status: str) -> str:
    """SUBMITTED -> RETURNED_FOR_CORRECTION (TAP administrative review or
    John Crane technical review, caller distinguishes by actor column)."""
    guard_transition(current_status, RETURNED_FOR_CORRECTION)
    return RETURNED_FOR_CORRECTION


def finalize(current_status: str, technical_outcome: str) -> str:
    """SUBMITTED -> FINALIZED, only via a John Crane technical-review
    action with a real outcome (Phase 13/15)."""
    if technical_outcome not in TECHNICAL_OUTCOMES:
        raise ValueError(f"technical_outcome must be one of {sorted(TECHNICAL_OUTCOMES)}, got {technical_outcome!r}")
    guard_transition(current_status, FINALIZED)
    return FINALIZED


__all__ = [
    "DRAFT",
    "SUBMITTED",
    "RETURNED_FOR_CORRECTION",
    "FINALIZED",
    "ACKNOWLEDGED",
    "TECHNICALLY_APPROVED",
    "TECHNICAL_OUTCOMES",
    "InvalidTransitionError",
    "RecordNotEditableError",
    "is_editable",
    "guard_editable",
    "guard_transition",
    "submit",
    "return_for_correction",
    "finalize",
]
