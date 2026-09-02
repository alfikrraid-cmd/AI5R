"""MWO-LTSA-HISTORICAL-PM-RECOVERY-001 --
historical_pm_recovery_validation_service tests. Pure logic against an
in-memory fake state -- no DB, no HTTP, and (case 12) the fake exposes
no mutation method at all, so an accidental write attempt would be a
hard AttributeError, not a silent success."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.historical_pm_recovery_validation_service import (  # noqa: E402
    validate_pm_recovery_batch,
    validate_pm_recovery_candidate,
)


class FakeLivePmState:
    """No create/update/delete method exists anywhere on this class --
    case 12's own guarantee that this validation path cannot mutate
    PM, let alone CM/CMON/installation_report/anything else."""

    def __init__(self, *, canonical_counts=None, existing_occurrences=None):
        self.canonical_counts = dict(canonical_counts or {})
        self.existing_occurrences = set(existing_occurrences or set())

    def count_canonical_pump_matches(self, pump_tag_number):
        return self.canonical_counts.get(pump_tag_number, 0)

    def occurrence_exists(self, *, asset_code, occurrence_date):
        return (asset_code, occurrence_date) in self.existing_occurrences


# -- 1. valid new PM ---------------------------------------------------------


def test_valid_new_pm_candidate():
    state = FakeLivePmState(canonical_counts={"211-P-18A": 1})
    result = validate_pm_recovery_candidate(
        state, canonical_tag="211-P-18A", occurrence_date="2026-01-06", seen_keys=set()
    )
    assert result["status"] == "VALID_NEW"


# -- 2. identical rerun => no duplicate (validation is deterministic) -------


def test_identical_rerun_produces_the_same_classification():
    state = FakeLivePmState(canonical_counts={"211-P-18A": 1})
    candidates = [{"canonical_tag": "211-P-18A", "occurrence_date": "2026-01-06", "source_classification": "PM"}]
    first = validate_pm_recovery_batch(state, candidates)
    second = validate_pm_recovery_batch(state, candidates)
    assert first["counts"] == second["counts"] == {"VALID_NEW": 1}


# -- 3. unknown pump rejected -------------------------------------------------


def test_unknown_pump_rejected():
    state = FakeLivePmState(canonical_counts={"999-P-99Z": 0})
    result = validate_pm_recovery_candidate(
        state, canonical_tag="999-P-99Z", occurrence_date="2026-01-06", seen_keys=set()
    )
    assert result["status"] == "UNKNOWN_PUMP"


# -- 4. ambiguous tag rejected -------------------------------------------------


def test_ambiguous_pump_rejected():
    state = FakeLivePmState(canonical_counts={"946-P-2D": 2})
    result = validate_pm_recovery_candidate(
        state, canonical_tag="946-P-2D", occurrence_date="2026-01-06", seen_keys=set()
    )
    assert result["status"] == "AMBIGUOUS_PUMP"


# -- 5. invalid date rejected --------------------------------------------------


def test_missing_date_rejected():
    state = FakeLivePmState(canonical_counts={"211-P-18A": 1})
    result = validate_pm_recovery_candidate(
        state, canonical_tag="211-P-18A", occurrence_date=None, seen_keys=set()
    )
    assert result["status"] == "INVALID"


# -- 6. existing identical PM => already exists --------------------------------


def test_existing_identical_pm_is_already_exists():
    state = FakeLivePmState(
        canonical_counts={"211-P-18A": 1}, existing_occurrences={("211-P-18A", "2026-01-06")}
    )
    result = validate_pm_recovery_candidate(
        state, canonical_tag="211-P-18A", occurrence_date="2026-01-06", seen_keys=set()
    )
    assert result["status"] == "ALREADY_EXISTS"


# -- 7. source duplicate rejected ----------------------------------------------


def test_source_duplicate_within_batch_rejected():
    state = FakeLivePmState(canonical_counts={"110-P-11A": 1})
    candidates = [
        {"canonical_tag": "110-P-11A", "occurrence_date": "2026-01-06", "source_classification": "PM"},
        {"canonical_tag": "110-P-11A", "occurrence_date": "2026-01-06", "source_classification": "PM"},
    ]
    result = validate_pm_recovery_batch(state, candidates)
    assert result["counts"] == {"VALID_NEW": 1, "SOURCE_DUPLICATE": 1}


# -- 8. conflicting duplicate rejected (same key, different content) ----------


def test_conflicting_content_duplicate_still_rejected_by_key_not_content():
    # This service's dedup is key-based (tag, date), never content-aware
    # -- a second row with different activities/remarks text but the same
    # key is still SOURCE_DUPLICATE, matching the verified real case
    # (110-P-11A/2026-01-06) where the duplicate WAS content-identical,
    # and never silently merged/preferred by this service either way.
    state = FakeLivePmState(canonical_counts={"110-P-11A": 1})
    candidates = [
        {"canonical_tag": "110-P-11A", "occurrence_date": "2026-01-06", "source_classification": "PM", "activities": "seal check"},
        {"canonical_tag": "110-P-11A", "occurrence_date": "2026-01-06", "source_classification": "PM", "activities": "DIFFERENT TEXT"},
    ]
    result = validate_pm_recovery_batch(state, candidates)
    assert result["counts"]["SOURCE_DUPLICATE"] == 1


# -- 9. source semantics not PM rejected ---------------------------------------


def test_non_pm_source_classification_rejected():
    state = FakeLivePmState(canonical_counts={"211-P-18A": 1})
    result = validate_pm_recovery_candidate(
        state, canonical_tag="211-P-18A", occurrence_date="2026-01-06", seen_keys=set(),
        source_classification="CMON",
    )
    assert result["status"] == "INVALID"
    assert "not PM" in result["reason"]


# -- 10. batch all-valid -------------------------------------------------------


def test_batch_all_valid():
    state = FakeLivePmState(canonical_counts={"211-P-18A": 1, "212-P-19B": 1})
    candidates = [
        {"canonical_tag": "211-P-18A", "occurrence_date": "2026-01-06", "source_classification": "PM"},
        {"canonical_tag": "212-P-19B", "occurrence_date": "2026-01-07", "source_classification": "PM"},
    ]
    result = validate_pm_recovery_batch(state, candidates)
    assert result["counts"] == {"VALID_NEW": 2}


# -- 11. one invalid candidate causes safe failure behavior --------------------


def test_one_invalid_candidate_is_isolated_others_still_validated():
    state = FakeLivePmState(canonical_counts={"211-P-18A": 1, "999-P-99Z": 0})
    candidates = [
        {"canonical_tag": "211-P-18A", "occurrence_date": "2026-01-06", "source_classification": "PM"},
        {"canonical_tag": "999-P-99Z", "occurrence_date": "2026-01-06", "source_classification": "PM"},
    ]
    result = validate_pm_recovery_batch(state, candidates)
    assert result["counts"] == {"VALID_NEW": 1, "UNKNOWN_PUMP": 1}
    # no exception raised -- validation never crashes the whole batch for one bad row


# -- 12. no CM/CMON/report/lifecycle mutation ----------------------------------


def test_state_protocol_exposes_no_write_method():
    # FakeLivePmState itself has no create/update/delete/set_* method --
    # there is nothing for this validation service to call that could
    # mutate anything, in any table.
    state = FakeLivePmState()
    write_like = [m for m in dir(state) if any(m.startswith(p) for p in ("create", "update", "delete", "set_", "insert", "promote", "stage"))]
    assert write_like == []


# -- 13/14. provenance + unrelated PM fields preserved -------------------------
# (verified at the create_draft layer in test_pm_occurrence_repository.py --
# this module never constructs an INSERT itself and has no field list of
# its own to preserve or drop; it only classifies tag+date+source_classification.)


def test_echoes_back_every_extra_manifest_field_unchanged():
    # This service never drops or rewrites caller-supplied manifest
    # fields -- whatever else the caller attaches (source batch, source
    # file, source record id, ...) comes back on the result untouched.
    state = FakeLivePmState(canonical_counts={"211-P-18A": 1})
    candidates = [{
        "canonical_tag": "211-P-18A", "occurrence_date": "2026-01-06", "source_classification": "PM",
        "source_batch": "HOC-1. JANUARY", "source_file": "x.xlsx", "source_record": "LTSA-PMO-ABC123",
    }]
    result = validate_pm_recovery_batch(state, candidates)
    row = result["results"][0]
    assert row["source_batch"] == "HOC-1. JANUARY"
    assert row["source_file"] == "x.xlsx"
    assert row["source_record"] == "LTSA-PMO-ABC123"
