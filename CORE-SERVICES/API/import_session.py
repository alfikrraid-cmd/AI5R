"""
MWO-LTSA-077 -- Import Session Manager: the canonical Import Session layer
sitting above the two already-existing, unmodified pipelines this MWO
explicitly forbids touching:
  - Knowledge Manufacturing (MWO-LTSA-074, PRODUCTS/LTSA-BRAIN/
    KNOWLEDGE-MANUFACTURING-PACK/knowledge_dataclasses.py) -- produces one
    CanonicalKnowledgePackage per raw source document.
  - Import Validator (MWO-LTSA-076, import_validator.py, this directory) --
    produces one ValidatedImportPackage (errors/warnings/relationships/
    summary) per canonical import package.

This module builds neither of those -- it takes ALREADY-BUILT
CanonicalKnowledgePackage / ValidatedImportPackage instances (supplied by
the caller, one-to-one, same order) and aggregates them into one immutable
ImportSession: session-level identity, a status drawn from a closed
vocabulary, session-wide statistics, and a session-wide validation summary.
Same composition style as recommendation_context.py's
build_recommendation_context(lifecycle) -- a pure function of an
already-built upstream object, never a second computation of what that
object already computed.

--------------------------------------------------------------------------
MWO-LTSA-085 -- Persistent Import Session (this revision)
--------------------------------------------------------------------------
Gap this closes, verbatim from the mission: "Today ImportSession only
stores metadata. It does NOT persist everything required for Execute."
Confirmed by reading CORE-SERVICES/BACKEND-API/routers/import_router.py's
own POST .../execute handler, whose comment already documented the exact
same gap -- ImportExecutionEngine.execute_import() needs a session's
ValidatedImportPackage and ConflictReport, and neither was ever stored on
ImportSession, only transiently used to compute a summary and discarded.

Three fields added, none rebuilt/revalidated/rerun -- each is the caller's
own already-built object, stored verbatim:
  - validated_packages: the exact `validations` sequence this builder
    already received (MWO-LTSA-076's validate_import_package() output) --
    previously used once to compute `statistics`/`validation_summary`
    then thrown away; now also kept.
  - conflict_report: one ConflictReport (MWO-LTSA-079's
    build_conflict_report() output) for the whole session -- optional,
    since a session's conflict report is only known once Relationship/
    Conflict Resolution has actually run (status REVIEWING or later).
  - execution_plan: the exact tuple[PlannedWrite, ...]
    import_execution_engine.build_execution_plan() (MWO-LTSA-081; made
    public by this MWO -- see that module's own header note) already
    computed -- "Store the plan produced by ImportExecutionEngine. Do not
    regenerate later." This module calls build_execution_plan() itself
    (it is a pure, no-I/O function, safe and correct to call from here),
    but never re-implements its own planning logic.
  - execution_result: the exact ImportExecutionResult
    import_execution_engine.execute_import() (MWO-LTSA-081) returned --
    optional/nullable, since most of a session's life has no result yet.

Status vocabulary extended by one value, additive only (no existing value
renamed or removed -- every prior IMPORT_SESSION_STATUSES check anywhere
in this codebase still passes): "EXECUTING" is inserted between APPROVED
and IMPORTED, matching this MWO's own explicit lifecycle diagram.

advance_import_session(session, **changes) is new: the "update" half of
the Session Repository's contract needs some way to produce the NEXT
ImportSession in a session's life (immutable dataclasses can never be
mutated in place) without forcing every caller to re-pass every unchanged
field by hand. It is a thin, transparent wrapper over stdlib
dataclasses.replace() -- not a second builder, not new business logic --
and always recomputes `statistics`/`validation_summary` fresh from
whatever validated_packages/conflict_report/execution_result the new
session now holds (never carries forward a stale derived number).

Backend only. No frontend, no parser, no database write, no SQL migration
-- this module performs no I/O of any kind.

Reuse, not a duplicate engine: DOCUMENT_TYPES-style closed-vocabulary
validation (IMPORT_SESSION_STATUSES here), the frozen/slots dataclass
convention, the TYPE_CHECKING-only cross-module type reference pattern
(recommendation_context.py's own `if TYPE_CHECKING: from .pump_lifecycle_models
import ...`), and the "every derived number is len()/sum() of a real
input list, never a separately-tracked count" discipline (import_validator.py's
own ImportSummary docstring) are all reused verbatim below, not
reinvented.

Deterministic, no auto-generation: session_id and created_at are both
required caller-supplied strings -- this module contains no
uuid.uuid4()/datetime.now() call anywhere. Given the same inputs twice,
build_import_session()/advance_import_session() return equal
ImportSession instances field-for-field.

--------------------------------------------------------------------------
MWO-LTSA-102B -- Canonical Import Pipeline (this revision)
--------------------------------------------------------------------------
Resolves the architecture gap MWO-LTSA-096/099/102/102A each independently
hit and disclosed rather than papering over: `packages` is declared
`tuple["CanonicalKnowledgePackage", ...]` (this dataclass's own field, line
below) and always was, but the one real caller with a many-entity input
(import_router.py's POST .../session) was passing a raw, plural
API.import_validator.ImportPackage instead -- a real type-contract
violation that would only ever surface as an AttributeError deep inside
ImportExecutionEngine.to_sql_ready_dto(), the first time that endpoint's
own execute stub was ever wired up for real.

Chief Architect decision (MWO-LTSA-102A/102B), verbatim: "ImportPackage
[is eliminated from] the execution path" -- it remains the external
adapt/validate/conflict-check DTO (import_adapter.py/import_validator.py/
conflict_resolution.py, all untouched by this MWO), but ImportSession/
ImportExecutionEngine/ImportWorker/ImportQueue must receive
CanonicalKnowledgePackage only, from here on.

build_canonical_packages(package) is the one, minimal, fully-disclosed
function this closes the gap with -- NOT a converter/bridge/adapter (this
mission's own explicit "never create" list): it renames no field,
transforms no value, makes no business decision. ImportPackage's own
tuples are split one-entity-per-raw_document using Knowledge
Manufacturing's own existing, unmodified vocabulary ("pump"/"seal"/
"installation"/"documents" -- the exact keys knowledge_pipeline.extract()
already reads), then handed to manufacture_knowledge_packages()
(knowledge_pipeline.py, MWO-LTSA-102B's own EXTENSION of the existing,
single Knowledge Manufacturing pipeline -- not a second one). Every real
stage (Extraction/Normalization/Validation/Relationship-Resolution/
Canonical-Object) still happens exactly once, inside Knowledge
Manufacturing, reused unmodified.

Field-coverage compatibility confirmed before writing this function:
knowledge_validators.REQUIRED_FIELDS's own pump/seal/installation/document
requirements are each an equal-or-looser subset of import_validator.py's
own required-field rules for the same entities (pump: KMP needs only
tag_number, import_validator also requires area; seal: KMP needs only
seal_code, import_validator also requires seal_name; installation: KMP
skips source_document_name, import_validator requires it; document: both
require exactly document_code/seal_code/document_type/title). Any package
that already passed API.import_validator.validate_import_package() is
therefore guaranteed to also pass manufacture_knowledge_package()'s own
internal validate() call -- this function never has to reconcile a
contradiction between the two validators (and never re-implements either
one).

`packages`/`validated_packages` no longer need matching lengths (the
length-equality check build_import_session()/advance_import_session() both
used to enforce is REMOVED, not weakened-and-kept): they describe
different granularities now that packages genuinely holds one entry per
CanonicalKnowledgePackage (many, per incoming batch) while
validated_packages holds one ValidatedImportPackage per incoming
ImportPackage batch as a whole (validate_import_package()'s own
relationship-checking is inherently a whole-batch computation, e.g. "does
this installation's plant_equip_no resolve to a pump in this SAME
package" -- splitting it per-entity would silently lose that cross-entity
signal, so this module does not attempt to). import_execution_engine.py
already only ever reads len(session.validated_packages) itself
(ImportWorker's own MWO-LTSA-096 rule, unchanged, unrelated to this
length-equality removal).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from conflict_resolution import ConflictReport
    from import_execution_engine import ImportExecutionResult, PlannedWrite
    from import_validator import ImportError, ImportPackage, ImportWarning, ValidatedImportPackage

    # CanonicalKnowledgePackage itself stays a type-only reference here --
    # this module holds instances the caller (or, since MWO-LTSA-102B,
    # build_canonical_packages() below) already built, never re-implementing
    # the Knowledge Manufacturing pipeline itself.
    from knowledge_dataclasses import CanonicalKnowledgePackage

# --------------------------------------------------------------------------
# MWO-LTSA-102B -- real (not TYPE_CHECKING-only) Knowledge Manufacturing
# import, needed because build_canonical_packages() below actually CALLS
# manufacture_knowledge_packages() at runtime (not just referencing its
# return type). The sys.path insertion is therefore real too now -- the
# same KMP path every other CORE-SERVICES/API module that reuses Knowledge
# Manufacturing (pdf_import_parser.py, import_cli.py) already adds, not a
# new pattern.
# --------------------------------------------------------------------------
_KMP_PATH = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "KNOWLEDGE-MANUFACTURING-PACK"
if str(_KMP_PATH) not in sys.path:
    sys.path.insert(0, str(_KMP_PATH))

from knowledge_pipeline import manufacture_knowledge_packages  # noqa: E402

# --- Real runtime import ------------------------------------------------
# build_execution_plan() is a pure, no-I/O function (confirmed by reading
# import_execution_engine.py before reuse) -- calling it here to populate
# `execution_plan` is not "re-running an engine", it is this module's own
# stated job: "Store the plan produced by ImportExecutionEngine."
#
# Relative import (not a bare/sys.path-shimmed one): this module is always
# loaded as `API.import_session` by every real caller (test files, the
# FastAPI router, both `from API.import_session import ...`), matching
# conflict_resolution.py's own established `from .import_validator import
# ImportPackage` convention. A bare `from import_execution_engine import
# ...` would create a SECOND, separately-cached module object
# (`sys.modules["import_execution_engine"]` vs
# `sys.modules["API.import_execution_engine"]`) -- same source file, but a
# different `PlannedWrite` class object, so `PlannedWrite` instances built
# via the two different import paths would compare unequal even when
# field-for-field identical (dataclass `__eq__` requires the same class
# object). Confirmed by hitting exactly this bug while testing this
# module -- the relative import is the fix, not a style preference.
from .import_execution_engine import build_execution_plan  # noqa: E402

# Status vocabulary. MWO-LTSA-077's original 6 values, extended additively
# by MWO-LTSA-085 with "EXECUTING" (between APPROVED and IMPORTED, per this
# MWO's own explicit lifecycle diagram) -- the same
# "value must be one of these, or it's an error" discipline
# import_validator.py's own DOCUMENT_TYPES CHECK-constraint validation
# already established.
IMPORT_SESSION_STATUSES = ("NEW", "VALIDATED", "REVIEWING", "APPROVED", "EXECUTING", "IMPORTED", "FAILED")


@dataclass(frozen=True, slots=True)
class ImportSessionStatistics:
    """Counts only -- every number here is len()/sum()/count()-derived
    from the real validated_packages/conflict_report/execution_result a
    session holds, never a separately-tracked or duplicated counter (same
    discipline import_validator.ImportSummary's own docstring already
    states). Conflict/execution counts are 0 whenever the corresponding
    input is still absent (a session that hasn't reached REVIEWING/
    EXECUTING yet) -- an honest "not yet known", never a fabricated
    number."""

    total_packages: int
    valid_packages: int
    invalid_packages: int
    warning_packages: int
    conflict_count: int
    inserted: int
    updated: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class ImportSessionValidationSummary:
    """Every ImportError/ImportWarning from every package's own
    ValidatedImportPackage, flattened into one session-wide view --
    concatenation only, no re-validation, no re-derivation."""

    errors: tuple["ImportError", ...]
    warnings: tuple["ImportWarning", ...]


@dataclass(frozen=True, slots=True)
class ImportSession:
    """Immutable. The canonical container for ONE import operation
    (MWO-LTSA-085): identity (session_id/created_at/source/created_by, all
    caller-supplied, never generated), a status drawn from
    IMPORT_SESSION_STATUSES, every object Execute needs
    (packages/validated_packages/conflict_report/execution_plan/
    execution_result), and the derived statistics/validation_summary.
    Nothing here is rebuilt/revalidated/rerun -- every field is either a
    caller-supplied already-built object or a pure derivation of the
    others."""

    session_id: str
    created_at: str
    source: str
    created_by: str | None
    status: str
    packages: tuple["CanonicalKnowledgePackage", ...]
    validated_packages: tuple["ValidatedImportPackage", ...]
    conflict_report: "ConflictReport | None"
    execution_plan: tuple["PlannedWrite", ...]
    execution_result: "ImportExecutionResult | None"
    statistics: ImportSessionStatistics
    validation_summary: ImportSessionValidationSummary


def build_import_session(
    *,
    session_id: str,
    created_at: str,
    source: str,
    status: str,
    packages: Sequence["CanonicalKnowledgePackage"] = (),
    validations: Sequence["ValidatedImportPackage"] = (),
    conflict_report: "ConflictReport | None" = None,
    execution_result: "ImportExecutionResult | None" = None,
    created_by: str | None = None,
) -> ImportSession:
    """The one builder. Pure -- no I/O, no database, no filesystem, no
    generated id/timestamp (session_id/created_at are required arguments,
    not defaults). Accepts EXISTING objects only: `packages` is real
    CanonicalKnowledgePackage instances (MWO-LTSA-102B -- build_canonical_
    packages() below turns an ImportPackage into these; this builder never
    accepts a raw ImportPackage), `validations` is MWO-LTSA-076's own
    validate_import_package() output, `conflict_report` is MWO-LTSA-079's
    own build_conflict_report() output, `execution_result` is MWO-LTSA-081's
    own execute_import() output -- none is rebuilt, revalidated, or rerun
    here. `execution_plan` is derived from `conflict_report` via
    build_execution_plan() (a pure function, see this module's own header
    note) whenever a conflict_report is given; the underlying
    ImportExecutionEngine is never re-run.

    `packages` and `validations` are independent sequences, NOT required to
    be the same length (MWO-LTSA-102B removed that check -- see this
    module's own header for why: packages is one entry per
    CanonicalKnowledgePackage entity, typically many per incoming batch;
    validations is one ValidatedImportPackage per incoming ImportPackage
    batch as a whole, typically exactly one)."""
    if status not in IMPORT_SESSION_STATUSES:
        raise ValueError(
            f"status {status!r} is not one of {IMPORT_SESSION_STATUSES}"
        )

    execution_plan = _derive_execution_plan(packages, conflict_report)

    return ImportSession(
        session_id=session_id,
        created_at=created_at,
        source=source,
        created_by=created_by,
        status=status,
        packages=tuple(packages),
        validated_packages=tuple(validations),
        conflict_report=conflict_report,
        execution_plan=execution_plan,
        execution_result=execution_result,
        statistics=_build_statistics(validations, conflict_report, execution_result),
        validation_summary=_build_validation_summary(validations),
    )


def advance_import_session(session: ImportSession, **changes: Any) -> ImportSession:
    """Produces the NEXT ImportSession in a session's life -- the "update"
    half of the Session Repository contract. A thin wrapper over stdlib
    dataclasses.replace(): every field not named in `changes` carries
    forward from `session` unchanged; `statistics`/`validation_summary`
    are always recomputed fresh from whatever validated_packages/
    conflict_report/execution_result the result now holds (never a stale
    carried-forward number), and `execution_plan` is re-derived only if a
    new `conflict_report` was supplied (otherwise the existing plan
    carries forward unchanged, per "Do not regenerate later").

    Example: advance_import_session(session, status="REVIEWING",
    conflict_report=report) -- everything else (packages, validated_packages,
    identity) stays exactly as it was.

    `packages`/`validated_packages` are not required to be the same length
    (MWO-LTSA-102B -- same reasoning as build_import_session()'s own
    docstring: they describe different granularities now)."""
    if "status" in changes and changes["status"] not in IMPORT_SESSION_STATUSES:
        raise ValueError(f"status {changes['status']!r} is not one of {IMPORT_SESSION_STATUSES}")

    next_packages = changes.get("packages", session.packages)
    next_validations = changes.get("validated_packages", session.validated_packages)

    next_conflict_report = changes.get("conflict_report", session.conflict_report)
    next_execution_result = changes.get("execution_result", session.execution_result)

    next_execution_plan = (
        _derive_execution_plan(next_packages, next_conflict_report)
        if "conflict_report" in changes or "packages" in changes or "validated_packages" in changes
        else session.execution_plan
    )

    updated = replace(
        session,
        **changes,
        packages=tuple(next_packages),
        validated_packages=tuple(next_validations),
        execution_plan=next_execution_plan,
        statistics=_build_statistics(next_validations, next_conflict_report, next_execution_result),
        validation_summary=_build_validation_summary(next_validations),
    )
    return updated


def build_canonical_packages(package: "ImportPackage") -> tuple["CanonicalKnowledgePackage", ...]:
    """MWO-LTSA-102B -- the one, minimal, disclosed structural step between
    ImportPackage (API.import_validator.py's own many-entity-per-package
    DTO -- what UniversalImportAdapter/validate_import_package/
    build_conflict_report all produce/consume) and the CanonicalKnowledge
    Package instances ImportSession.packages/ImportExecutionEngine/
    ImportWorker require. See this module's own header for the full
    rationale (why this is not a converter/bridge/adapter, why field
    coverage is confirmed compatible, why packages/validated_packages no
    longer need matching lengths).

    Not a converter/bridge/adapter: no field is renamed, no value is
    transformed, no business decision is made here. ImportPackage's own
    tuples are simply split one-entity-per-raw_document, using Knowledge
    Manufacturing's own existing vocabulary ("pump"/"seal"/"installation"/
    "documents" -- the exact keys knowledge_pipeline.extract() already
    reads), then handed to manufacture_knowledge_packages() (knowledge_
    pipeline.py, this same MWO's own extension of that one pipeline, not a
    second one).

    Documents are never matched to a specific pump/seal/installation here
    (no cross-reference guessing): ImportPackage.documents carries no such
    link, so every document rides in its own package
    (pump=None/seal=None/installation=None, documents=(...)) -- an honest,
    undecided grouping, never a fabricated one. Raises
    ManufacturingValidationError (propagated from manufacture_knowledge_
    packages(), reused unmodified) if any entity is missing a field
    Knowledge Manufacturing's own validator requires."""
    raw_documents: list[dict[str, Any]] = []
    raw_documents.extend({"pump": pump} for pump in package.pumps)
    raw_documents.extend({"seal": seal} for seal in package.seals)
    raw_documents.extend({"installation": installation} for installation in package.installations)
    if package.documents:
        raw_documents.append({"documents": list(package.documents)})
    return manufacture_knowledge_packages(raw_documents)


def _derive_execution_plan(
    packages: Sequence[Any],
    conflict_report: "ConflictReport | None",
) -> tuple["PlannedWrite", ...]:
    if conflict_report is None or not packages:
        return ()

    # build_execution_plan() only reads session.packages/conflicts (a pure
    # function of those two values, confirmed by reading
    # import_execution_engine.py) -- a lightweight structural stand-in
    # satisfies it without importing ImportSession itself (which would be
    # a circular import, this module defining ImportSession).
    class _SessionView:
        def __init__(self, packages: tuple[Any, ...]) -> None:
            self.packages = packages

    return tuple(build_execution_plan(_SessionView(tuple(packages)), conflict_report))


def _build_statistics(
    validations: Sequence["ValidatedImportPackage"],
    conflict_report: "ConflictReport | None",
    execution_result: "ImportExecutionResult | None",
) -> ImportSessionStatistics:
    total = len(validations)
    valid = sum(1 for validation in validations if validation.summary.is_valid)
    invalid = total - valid
    with_warnings = sum(1 for validation in validations if validation.summary.warning_count > 0)

    conflict_count = conflict_report.conflict_count if conflict_report is not None else 0

    inserted = updated = skipped = failed = 0
    if execution_result is not None and execution_result.statistics is not None:
        for entity_stats in (
            execution_result.statistics.pump,
            execution_result.statistics.seal,
            execution_result.statistics.installation,
            execution_result.statistics.document,
        ):
            inserted += entity_stats.inserted
            updated += entity_stats.updated
            skipped += entity_stats.skipped
            failed += entity_stats.failed

    return ImportSessionStatistics(
        total_packages=total,
        valid_packages=valid,
        invalid_packages=invalid,
        warning_packages=with_warnings,
        conflict_count=conflict_count,
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        failed=failed,
    )


def _build_validation_summary(validations: Sequence["ValidatedImportPackage"]) -> ImportSessionValidationSummary:
    errors: list[Any] = []
    warnings: list[Any] = []
    for validation in validations:
        errors.extend(validation.errors)
        warnings.extend(validation.warnings)
    return ImportSessionValidationSummary(errors=tuple(errors), warnings=tuple(warnings))


__all__ = [
    "IMPORT_SESSION_STATUSES",
    "ImportSession",
    "ImportSessionStatistics",
    "ImportSessionValidationSummary",
    "build_import_session",
    "advance_import_session",
    "build_canonical_packages",
]
