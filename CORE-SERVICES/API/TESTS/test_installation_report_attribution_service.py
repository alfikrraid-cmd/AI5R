"""MWO-LTSA-INSTALLATION-REPORT-HISTORICAL-ATTRIBUTION-001 --
installation_report_attribution_service tests. Pure logic against an
in-memory fake -- no DB, no HTTP, mirrors test_whatsapp_registration_service.py's
own style for this same class of guarded admin-linking operation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.installation_report_attribution_service import (  # noqa: E402
    AmbiguousPumpTagError,
    ConflictingAttributionError,
    InstallationReportNotFoundError,
    UnknownPumpTagError,
    apply_pump_tag_backfill_batch,
    backfill_installation_report_pump_tag,
    validate_pump_tag_backfill_batch,
)


class FakeAttributionRepository:
    """report rows keyed by installation_code; pump tags is the exact
    canonical roster (never fuzzy/normalized -- this service has no tag
    normalizer of its own and none exists to reuse for pump tags)."""

    def __init__(self, *, reports=None, canonical_pump_counts=None, fail_atomic_batch_with=None):
        self.reports = {k: dict(v) for k, v in (reports or {}).items()}
        self.canonical_pump_counts = dict(canonical_pump_counts or {})
        self.write_calls = 0
        self.atomic_batch_calls = 0
        # When set, simulates the DB-side script itself raising (e.g. a
        # postcheck DO block) -- the fake must behave like Postgres: NO
        # row is changed, exactly like a real ROLLBACK.
        self._fail_atomic_batch_with = fail_atomic_batch_with

    def find_by_installation_code(self, installation_code):
        row = self.reports.get(installation_code)
        return dict(row) if row is not None else None

    def count_canonical_pump_matches(self, pump_tag_number):
        return self.canonical_pump_counts.get(pump_tag_number, 0)

    def set_pump_tag_number_if_unset(self, *, installation_code, pump_tag_number):
        self.write_calls += 1
        report = self.reports.get(installation_code)
        if report is None or report.get("pump_tag_number") is not None:
            return None
        report["pump_tag_number"] = pump_tag_number
        return {"installation_code": installation_code, "pump_tag_number": pump_tag_number}

    def backfill_pump_tags_batch_atomic(self, mappings):
        # Simulates Postgres's own guarantee for the real script: either
        # every mapping's guard holds and every row changes together, or
        # (if _fail_atomic_batch_with is set) NOTHING changes at all --
        # never a partial in-between state, mirroring the real DB-side
        # precheck/postcheck DO blocks aborting the whole transaction.
        self.atomic_batch_calls += 1
        if self._fail_atomic_batch_with is not None:
            raise self._fail_atomic_batch_with
        for m in mappings:
            report = self.reports.get(m["installation_code"])
            if report is None or report.get("pump_tag_number") is not None:
                raise RuntimeError(f"atomic batch precheck would have failed for {m['installation_code']!r}")
            if self.canonical_pump_counts.get(m["pump_tag_number"], 0) != 1:
                raise RuntimeError(f"atomic batch precheck would have failed for {m['pump_tag_number']!r}")
        applied = []
        for m in mappings:
            self.reports[m["installation_code"]]["pump_tag_number"] = m["pump_tag_number"]
            applied.append({"installation_code": m["installation_code"], "pump_tag_number": m["pump_tag_number"]})
        return applied


def _repo(**overrides):
    reports = {
        "INSTL-001-2026": {
            "installation_code": "INSTL-001-2026",
            "pump_tag_number": None,
            "source_document_name": "SCAN 001 INSTALLATION REPORT 211-P-14B.pdf",
            "report_no": "001/INSTL/TAP/01-2026",
            "report_date": "2026-01-06",
        },
    }
    reports.update(overrides.pop("reports", {}))
    canonical = {"211-P-14B": 1}
    canonical.update(overrides.pop("canonical_pump_counts", {}))
    return FakeAttributionRepository(
        reports=reports, canonical_pump_counts=canonical,
        fail_atomic_batch_with=overrides.pop("fail_atomic_batch_with", None),
    )


# -- 1. NULL -> valid canonical tag = PASS ----------------------------------


def test_null_to_valid_canonical_tag_applies():
    repo = _repo()
    result = backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="211-P-14B")
    assert result["status"] == "APPLIED"
    assert repo.reports["INSTL-001-2026"]["pump_tag_number"] == "211-P-14B"


# -- 2. same tag rerun = IDEMPOTENT PASS ------------------------------------


def test_same_tag_rerun_is_idempotent_no_op():
    repo = _repo()
    backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="211-P-14B")
    writes_after_first = repo.write_calls
    result = backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="211-P-14B")
    assert result["status"] == "ALREADY_LINKED"
    assert repo.write_calls == writes_after_first  # no second write attempted
    assert repo.reports["INSTL-001-2026"]["pump_tag_number"] == "211-P-14B"


# -- 3. different existing tag = REJECT -------------------------------------


def test_different_existing_tag_is_rejected_never_overwritten():
    repo = _repo(
        reports={"INSTL-001-2026": {"installation_code": "INSTL-001-2026", "pump_tag_number": "211-P-14B",
                                     "source_document_name": "x", "report_no": "001", "report_date": "2026-01-06"}},
        canonical_pump_counts={"211-P-1A": 1},
    )
    with pytest.raises(ConflictingAttributionError):
        backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="211-P-1A")
    assert repo.reports["INSTL-001-2026"]["pump_tag_number"] == "211-P-14B"  # unchanged


# -- 4. unknown pump = REJECT ------------------------------------------------


def test_unknown_pump_is_rejected():
    repo = _repo(canonical_pump_counts={"999-P-99Z": 0})
    with pytest.raises(UnknownPumpTagError):
        backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="999-P-99Z")
    assert repo.reports["INSTL-001-2026"]["pump_tag_number"] is None


# -- 5. missing report = REJECT ----------------------------------------------


def test_missing_report_is_rejected():
    repo = _repo()
    with pytest.raises(InstallationReportNotFoundError):
        backfill_installation_report_pump_tag(repo, installation_code="INSTL-999-2026", pump_tag_number="211-P-14B")


# -- 6. ambiguous/noncanonical input: no normalizer exists for pump tags,   -
#       so a non-exact-match input (e.g. compact "211P14B") must REJECT,   -
#       never be guessed/normalized by this service.                       -


def test_noncanonical_compact_tag_is_rejected_not_guessed():
    repo = _repo(canonical_pump_counts={"211P14B": 0})  # compact form never matches the canonical dashed roster
    with pytest.raises(UnknownPumpTagError):
        backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="211P14B")


def test_ambiguous_canonical_roster_match_is_rejected():
    # A genuinely ambiguous master roster (>1 row for the same tag_number)
    # must never be resolved by guessing which one -- reported, not picked.
    repo = _repo(canonical_pump_counts={"211-P-14B": 2})
    with pytest.raises(AmbiguousPumpTagError):
        backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="211-P-14B")


# -- 7. unrelated report fields unchanged ------------------------------------


def test_unrelated_report_fields_are_never_touched():
    repo = _repo()
    backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="211-P-14B")
    row = repo.reports["INSTL-001-2026"]
    assert row["source_document_name"] == "SCAN 001 INSTALLATION REPORT 211-P-14B.pdf"
    assert row["report_no"] == "001/INSTL/TAP/01-2026"
    assert row["report_date"] == "2026-01-06"


# -- 8. no lifecycle event created -------------------------------------------


def test_never_touches_lifecycle_or_fitment_fields():
    repo = _repo()
    result = backfill_installation_report_pump_tag(repo, installation_code="INSTL-001-2026", pump_tag_number="211-P-14B")
    # The service's own result and the fake repository's row both carry no
    # seal_unit_id/installation_event_id/linked_by/link_reason concept at
    # all -- this module has no code path that could set them.
    assert set(result.keys()) == {"installation_code", "pump_tag_number", "status"}
    assert "seal_unit_id" not in repo.reports["INSTL-001-2026"]
    assert "installation_event_id" not in repo.reports["INSTL-001-2026"]


# -- 9. batch all-valid = PASS -----------------------------------------------


def test_batch_all_valid_applies_every_entry():
    repo = _repo(
        reports={
            "INSTL-001-2026": {"installation_code": "INSTL-001-2026", "pump_tag_number": None, "source_document_name": "a", "report_no": "1", "report_date": "d"},
            "INSTL-002-2026": {"installation_code": "INSTL-002-2026", "pump_tag_number": None, "source_document_name": "b", "report_no": "2", "report_date": "d"},
        },
        canonical_pump_counts={"211-P-14B": 1, "212-P-25A": 1},
    )
    mappings = [
        {"installation_code": "INSTL-001-2026", "pump_tag_number": "211-P-14B"},
        {"installation_code": "INSTL-002-2026", "pump_tag_number": "212-P-25A"},
    ]
    result = apply_pump_tag_backfill_batch(repo, mappings)
    assert result["status"] == "APPLIED"
    assert len(result["applied"]) == 2
    assert repo.reports["INSTL-001-2026"]["pump_tag_number"] == "211-P-14B"
    assert repo.reports["INSTL-002-2026"]["pump_tag_number"] == "212-P-25A"
    # Went through the ONE atomic call, not a per-row loop.
    assert repo.atomic_batch_calls == 1
    assert repo.write_calls == 0


# -- true single-transaction guarantee: a DB-side failure mid-batch must  ---
# -- leave EXACTLY zero rows changed, never a partial commit -----------------


def test_atomic_batch_db_failure_leaves_zero_rows_changed():
    repo = _repo(
        reports={
            "INSTL-001-2026": {"installation_code": "INSTL-001-2026", "pump_tag_number": None, "source_document_name": "a", "report_no": "1", "report_date": "d"},
            "INSTL-002-2026": {"installation_code": "INSTL-002-2026", "pump_tag_number": None, "source_document_name": "b", "report_no": "2", "report_date": "d"},
        },
        canonical_pump_counts={"211-P-14B": 1, "212-P-25A": 1},
        fail_atomic_batch_with=RuntimeError("simulated Postgres postcheck DO block RAISE EXCEPTION"),
    )
    mappings = [
        {"installation_code": "INSTL-001-2026", "pump_tag_number": "211-P-14B"},
        {"installation_code": "INSTL-002-2026", "pump_tag_number": "212-P-25A"},
    ]
    result = apply_pump_tag_backfill_batch(repo, mappings)
    assert result["status"] == "REJECTED_ATOMIC_TRANSACTION_FAILED"
    assert result["applied"] == []
    # The defining guarantee this fix exists for: NEITHER row changed,
    # not "the first one succeeded before the second one failed".
    assert repo.reports["INSTL-001-2026"]["pump_tag_number"] is None
    assert repo.reports["INSTL-002-2026"]["pump_tag_number"] is None


# -- 10. one invalid member causes zero batch mutation -----------------------


def test_batch_one_invalid_member_applies_nothing():
    repo = _repo(
        reports={
            "INSTL-001-2026": {"installation_code": "INSTL-001-2026", "pump_tag_number": None, "source_document_name": "a", "report_no": "1", "report_date": "d"},
            "INSTL-002-2026": {"installation_code": "INSTL-002-2026", "pump_tag_number": None, "source_document_name": "b", "report_no": "2", "report_date": "d"},
        },
        canonical_pump_counts={"211-P-14B": 1, "999-P-99Z": 0},
    )
    mappings = [
        {"installation_code": "INSTL-001-2026", "pump_tag_number": "211-P-14B"},
        {"installation_code": "INSTL-002-2026", "pump_tag_number": "999-P-99Z"},  # unknown pump
    ]
    result = apply_pump_tag_backfill_batch(repo, mappings)
    assert result["status"] == "REJECTED_PRECHECK_FAILED"
    assert result["applied"] == []
    assert repo.reports["INSTL-001-2026"]["pump_tag_number"] is None  # NOT applied despite being individually valid
    assert repo.reports["INSTL-002-2026"]["pump_tag_number"] is None
    assert repo.write_calls == 0


def test_batch_validate_only_never_writes():
    repo = _repo(canonical_pump_counts={"211-P-14B": 1})
    mappings = [{"installation_code": "INSTL-001-2026", "pump_tag_number": "211-P-14B"}]
    result = validate_pump_tag_backfill_batch(repo, mappings)
    assert result["all_valid"] is True
    assert repo.write_calls == 0
    assert repo.reports["INSTL-001-2026"]["pump_tag_number"] is None
