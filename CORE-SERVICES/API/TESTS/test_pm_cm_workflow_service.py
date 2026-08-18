"""MWO-LTSA-PM-CM-INTAKE-001 -- pure state-machine tests for the one
workflow shared by PM Occurrence and Condition Monitoring Reading."""

import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.pm_cm_workflow_service import (  # noqa: E402
    ACKNOWLEDGED,
    DRAFT,
    FINALIZED,
    RETURNED_FOR_CORRECTION,
    SUBMITTED,
    TECHNICALLY_APPROVED,
    InvalidTransitionError,
    RecordNotEditableError,
    finalize,
    guard_editable,
    guard_transition,
    is_editable,
    return_for_correction,
    submit,
)


def test_draft_is_editable():
    assert is_editable(DRAFT) is True
    guard_editable(DRAFT)  # does not raise


def test_returned_for_correction_is_editable():
    assert is_editable(RETURNED_FOR_CORRECTION) is True


def test_submitted_is_not_editable():
    assert is_editable(SUBMITTED) is False
    with pytest.raises(RecordNotEditableError):
        guard_editable(SUBMITTED)


def test_finalized_is_not_editable():
    assert is_editable(FINALIZED) is False
    with pytest.raises(RecordNotEditableError):
        guard_editable(FINALIZED)


def test_submit_from_draft():
    assert submit(DRAFT) == SUBMITTED


def test_submit_from_returned_for_correction():
    assert submit(RETURNED_FOR_CORRECTION) == SUBMITTED


def test_submit_from_submitted_is_illegal():
    with pytest.raises(InvalidTransitionError):
        submit(SUBMITTED)


def test_submit_from_finalized_is_illegal():
    with pytest.raises(InvalidTransitionError):
        submit(FINALIZED)


def test_return_for_correction_from_submitted():
    assert return_for_correction(SUBMITTED) == RETURNED_FOR_CORRECTION


def test_return_for_correction_from_draft_is_illegal():
    with pytest.raises(InvalidTransitionError):
        return_for_correction(DRAFT)


def test_finalize_from_submitted_with_acknowledged():
    assert finalize(SUBMITTED, ACKNOWLEDGED) == FINALIZED


def test_finalize_from_submitted_with_technically_approved():
    assert finalize(SUBMITTED, TECHNICALLY_APPROVED) == FINALIZED


def test_finalize_from_draft_is_illegal():
    with pytest.raises(InvalidTransitionError):
        finalize(DRAFT, ACKNOWLEDGED)


def test_finalize_with_an_invalid_outcome_is_rejected():
    with pytest.raises(ValueError):
        finalize(SUBMITTED, "MADE_UP_OUTCOME")


def test_finalized_has_no_further_legal_transitions():
    with pytest.raises(InvalidTransitionError):
        guard_transition(FINALIZED, SUBMITTED)
    with pytest.raises(InvalidTransitionError):
        guard_transition(FINALIZED, DRAFT)
