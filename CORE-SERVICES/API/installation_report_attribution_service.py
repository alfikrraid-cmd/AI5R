"""MWO-LTSA-INSTALLATION-REPORT-HISTORICAL-ATTRIBUTION-001 -- historical
EQUIPMENT ATTRIBUTION for installation_report, distinct from
installation_fitment_service.py's physical FITMENT/lifecycle linking:

    A. Historical attribution (this module):
       installation_report -> pump_tag_number
       (document says which pump; no lifecycle claim)

    B. Lifecycle/fitment linking (installation_fitment_service.py,
       untouched by this module):
       installation_report -> seal_unit -> seal_lifecycle_event -> pump

Attribution must never imply a lifecycle event exists: this module never
reads, writes, or requires seal_unit_id/installation_event_id/linked_by/
link_reason, and never creates seal_lifecycle_event/seal_unit/PM/CM/CMON
rows. installation_fitment_service.link_installation_report()'s own guard
(`report["pump_tag_number"] is not None and ... != pump_tag_number`)
already anticipates pump_tag_number being set independently of fitment --
this module is that independent path, not a repurposing of fitment.

Guarded, idempotent, single-field write: same report + same canonical tag
is a safe no-op (ALREADY_LINKED); same report + a different tag is a hard
conflict, never silently overwritten -- the same "guarded UPDATE ... WHERE
column IS NULL" one-time-transition shape link_installation_report()
already established for this exact table.

No new table, no new column, no fabricated actor: no linked_by is
required or invented here (attribution is not a fitment decision an
actor makes; it is a deterministic read of the report's own recorded
source_document_name).
"""

from __future__ import annotations

from typing import Any, Protocol


class InstallationReportAttributionError(ValueError):
    """Base class for every rejected attribution -- callers map each
    subtype to their own handling, never a bare failure."""


class InstallationReportNotFoundError(InstallationReportAttributionError):
    pass


class UnknownPumpTagError(InstallationReportAttributionError):
    pass


class AmbiguousPumpTagError(InstallationReportAttributionError):
    pass


class ConflictingAttributionError(InstallationReportAttributionError):
    pass


class AttributionRepositoryProtocol(Protocol):
    def find_by_installation_code(self, installation_code: str) -> dict[str, Any] | None: ...
    def count_canonical_pump_matches(self, pump_tag_number: str) -> int: ...
    def set_pump_tag_number_if_unset(self, *, installation_code: str, pump_tag_number: str) -> dict[str, Any] | None: ...


def _validate_one(
    repository: AttributionRepositoryProtocol, *, installation_code: str, pump_tag_number: str
) -> dict[str, Any]:
    """Read-only. Never writes. Returns a status dict; never raises --
    batch validation needs every entry's outcome, not just the first
    failure."""
    report = repository.find_by_installation_code(installation_code)
    if report is None:
        return {"installation_code": installation_code, "pump_tag_number": pump_tag_number, "status": "NOT_FOUND"}

    match_count = repository.count_canonical_pump_matches(pump_tag_number)
    if match_count == 0:
        return {"installation_code": installation_code, "pump_tag_number": pump_tag_number, "status": "UNKNOWN_PUMP"}
    if match_count > 1:
        return {"installation_code": installation_code, "pump_tag_number": pump_tag_number, "status": "AMBIGUOUS_PUMP"}

    current = report.get("pump_tag_number")
    if current is not None:
        if current == pump_tag_number:
            return {"installation_code": installation_code, "pump_tag_number": pump_tag_number, "status": "ALREADY_LINKED"}
        return {
            "installation_code": installation_code,
            "pump_tag_number": pump_tag_number,
            "status": "CONFLICT",
            "existing_pump_tag_number": current,
        }

    return {"installation_code": installation_code, "pump_tag_number": pump_tag_number, "status": "VALID"}


def validate_pump_tag_backfill(
    repository: AttributionRepositoryProtocol, *, installation_code: str, pump_tag_number: str
) -> dict[str, Any]:
    """Read-only precheck for a single report. Never writes."""
    return _validate_one(repository, installation_code=installation_code, pump_tag_number=pump_tag_number)


def backfill_installation_report_pump_tag(
    repository: AttributionRepositoryProtocol, *, installation_code: str, pump_tag_number: str
) -> dict[str, Any]:
    """Single guarded write. Idempotent on an exact repeat; raises on
    every other non-VALID outcome so a caller can never silently no-op a
    real conflict."""
    result = _validate_one(repository, installation_code=installation_code, pump_tag_number=pump_tag_number)
    status = result["status"]
    if status == "NOT_FOUND":
        raise InstallationReportNotFoundError(installation_code)
    if status == "UNKNOWN_PUMP":
        raise UnknownPumpTagError(pump_tag_number)
    if status == "AMBIGUOUS_PUMP":
        raise AmbiguousPumpTagError(pump_tag_number)
    if status == "CONFLICT":
        raise ConflictingAttributionError(
            f"installation_report {installation_code!r} already carries pump_tag_number "
            f"{result['existing_pump_tag_number']!r}, cannot backfill to {pump_tag_number!r}"
        )
    if status == "ALREADY_LINKED":
        return {"installation_code": installation_code, "pump_tag_number": pump_tag_number, "status": "ALREADY_LINKED"}

    updated = repository.set_pump_tag_number_if_unset(installation_code=installation_code, pump_tag_number=pump_tag_number)
    if updated is None:
        # Guard fired between the read above and this write -- a
        # genuinely concurrent attribution attempt won the race. Never
        # silently treated as success.
        raise ConflictingAttributionError(
            f"installation_report {installation_code!r} was attributed concurrently before this write"
        )
    return {"installation_code": installation_code, "pump_tag_number": updated["pump_tag_number"], "status": "APPLIED"}


def validate_pump_tag_backfill_batch(
    repository: AttributionRepositoryProtocol, mappings: list[dict[str, str]]
) -> dict[str, Any]:
    """Read-only. Validates every entry; never writes regardless of
    outcome. `mappings`: [{"installation_code": ..., "pump_tag_number": ...}, ...]."""
    results = [
        _validate_one(repository, installation_code=m["installation_code"], pump_tag_number=m["pump_tag_number"])
        for m in mappings
    ]
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"results": results, "counts": counts, "all_valid": counts.get("VALID", 0) == len(results)}


def apply_pump_tag_backfill_batch(
    repository: AttributionRepositoryProtocol, mappings: list[dict[str, str]]
) -> dict[str, Any]:
    """Fail-closed batch apply. Validates every entry first (read-only,
    zero writes); if any entry is not VALID, applies NOTHING and returns
    the validation report untouched -- "all 42 succeed or zero change".

    DatabaseRunner has no cross-call transaction primitive (every write
    here, like link_installation_report()'s own, is one guarded
    single-row UPDATE over its own connection) -- there is no existing
    multi-statement-transaction abstraction in this codebase to reuse,
    and building one is a larger change than this MWO's own "smallest
    safe mechanism" scope. Equivalent safety instead: the all-valid
    precheck below guarantees nothing is attempted unless every row is
    already known-safe, and each individual write stays guarded (WHERE
    pump_tag_number IS NULL) so a same-millisecond race still cannot
    silently overwrite -- it raises and this function stops immediately,
    reporting exactly how many rows were actually applied before the
    unexpected failure, rather than a false "all succeeded"."""
    precheck = validate_pump_tag_backfill_batch(repository, mappings)
    if not precheck["all_valid"]:
        return {"applied": [], "precheck": precheck, "status": "REJECTED_PRECHECK_FAILED"}

    applied: list[dict[str, Any]] = []
    for m in mappings:
        try:
            applied.append(
                backfill_installation_report_pump_tag(
                    repository, installation_code=m["installation_code"], pump_tag_number=m["pump_tag_number"]
                )
            )
        except InstallationReportAttributionError as error:
            return {
                "applied": applied,
                "precheck": precheck,
                "status": "PARTIAL_FAILURE_RACE",
                "failed_at": m["installation_code"],
                "error": str(error),
            }
    return {"applied": applied, "precheck": precheck, "status": "APPLIED"}


__all__ = [
    "InstallationReportAttributionError",
    "InstallationReportNotFoundError",
    "UnknownPumpTagError",
    "AmbiguousPumpTagError",
    "ConflictingAttributionError",
    "AttributionRepositoryProtocol",
    "validate_pump_tag_backfill",
    "backfill_installation_report_pump_tag",
    "validate_pump_tag_backfill_batch",
    "apply_pump_tag_backfill_batch",
]
