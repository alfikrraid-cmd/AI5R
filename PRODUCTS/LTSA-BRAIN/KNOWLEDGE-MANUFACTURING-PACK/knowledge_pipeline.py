"""MWO-LTSA-074 -- LTSA Knowledge Manufacturing Engine, pipeline orchestration.

    Raw Document
      -> Extraction              (extract)
      -> Normalization           (normalize, knowledge_normalizers.py)
      -> Validation               (validate, knowledge_validators.py)
      -> Relationship Resolution  (resolve_relationships, knowledge_relationship_resolver.py)
      -> Canonical Engineering Object  (build_canonical_package, knowledge_dataclasses.py)
      -> SQL-ready DTO             (to_sql_ready_dto)

Pure transformation only, per this MWO's explicit rule: no network call, no
file I/O, no database write, no AI/LLM/prompt anywhere in this module or
anything it imports (FACTORY.RESOLUTION.relationship_resolver.RelationshipResolver
and FACTORY.CORE.exceptions.ManufacturingValidationError are both read-only,
I/O-free platform interfaces, confirmed by inspection before reuse). Given
the same raw_document dict twice, `manufacture_knowledge_package` returns
two CanonicalKnowledgePackage instances that compare equal field-for-field --
no wall-clock timestamp, no random ID, no generated value anywhere in the
pipeline.

"Input is already extracted JSON. No OCR." -- the Extraction stage below
does not parse a PDF/image/workbook; it only reads the already-structured
top-level sections (`pump`, `installation`, `seal`, `drawing`, `pm`, `cm`,
`failure`, `workorder`, `documents`) a prior (out-of-scope, per this MWO)
extraction layer already produced. A raw_document missing a section simply
yields that package field as None/empty -- never fabricated.
"""

from __future__ import annotations

from typing import Any, Sequence

from knowledge_dataclasses import (
    CanonicalKnowledgePackage,
    CMObject,
    DocumentObject,
    DrawingObject,
    FailureObject,
    InstallationObject,
    KnowledgeRelationshipSummary,
    PMObject,
    PumpObject,
    SealObject,
    WorkOrderObject,
)
from knowledge_normalizers import normalize_dict, normalize_list
from knowledge_relationship_resolver import resolve_package_relationships
from knowledge_validators import validate_package

_SECTION_KEYS = ("pump", "installation", "seal", "drawing", "pm", "cm", "failure", "workorder", "documents")
_SINGULAR_SECTIONS = ("pump", "installation", "seal", "drawing")
_PLURAL_SECTIONS = ("pm", "cm", "failure", "workorder", "documents")


def extract(raw_document: dict[str, Any] | None) -> dict[str, Any]:
    """Extraction stage. Pulls out only the known top-level sections this
    pipeline understands -- never invents a section the input lacks, never
    reads anything else off raw_document (e.g. OCR confidence scores,
    page-image references -- those belong to the out-of-scope extraction
    layer upstream of this pipeline's input)."""
    raw_document = raw_document or {}
    extracted: dict[str, Any] = {}
    for key in _SINGULAR_SECTIONS:
        extracted[key] = raw_document.get(key)
    for key in _PLURAL_SECTIONS:
        extracted[key] = raw_document.get(key) or []
    return extracted


def normalize(extracted: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in _SINGULAR_SECTIONS:
        normalized[key] = normalize_dict(extracted.get(key)) or None
    for key in _PLURAL_SECTIONS:
        normalized[key] = normalize_list(extracted.get(key))
    return normalized


def validate(normalized: dict[str, Any]) -> None:
    validate_package(normalized)


def resolve_relationships(normalized: dict[str, Any]):
    return resolve_package_relationships(normalized)


def build_canonical_package(normalized: dict[str, Any], relationships) -> CanonicalKnowledgePackage:
    pump = PumpObject(**_project(normalized.get("pump"), PumpObject)) if normalized.get("pump") else None
    installation = (
        InstallationObject(**_project(normalized.get("installation"), InstallationObject))
        if normalized.get("installation")
        else None
    )
    seal = SealObject(**_project(normalized.get("seal"), SealObject)) if normalized.get("seal") else None
    drawing = (
        DrawingObject(**_project(normalized.get("drawing"), DrawingObject)) if normalized.get("drawing") else None
    )

    return CanonicalKnowledgePackage(
        pump=pump,
        installation=installation,
        seal=seal,
        drawing=drawing,
        pm=tuple(PMObject(**_project(item, PMObject)) for item in normalized.get("pm") or []),
        cm=tuple(CMObject(**_project(item, CMObject)) for item in normalized.get("cm") or []),
        failure=tuple(FailureObject(**_project(item, FailureObject)) for item in normalized.get("failure") or []),
        workorder=tuple(
            WorkOrderObject(**_project(item, WorkOrderObject)) for item in normalized.get("workorder") or []
        ),
        documents=tuple(
            DocumentObject(**_project(item, DocumentObject)) for item in normalized.get("documents") or []
        ),
        relationships=KnowledgeRelationshipSummary(
            resolved=dict(relationships.resolved), unresolved=tuple(relationships.unresolved)
        ),
    )


def _project(data: dict[str, Any] | None, dataclass_type: type) -> dict[str, Any]:
    """Projects a normalized dict onto a dataclass's own typed identity
    fields (everything the dataclass declares except `raw`), and always
    carries the complete dict forward unmodified as `raw` -- see
    knowledge_dataclasses.py's own header for why identity fields aren't
    the only source of truth."""
    data = data or {}
    field_names = [name for name in dataclass_type.__dataclass_fields__ if name != "raw"]
    projected = {name: data.get(name) for name in field_names}
    projected["raw"] = data
    return projected


def manufacture_knowledge_package(raw_document: dict[str, Any] | None) -> CanonicalKnowledgePackage:
    """The whole pipeline, one call: Extraction -> Normalization ->
    Validation -> Relationship Resolution -> Canonical Engineering Object.
    Raises ManufacturingValidationError (knowledge_validators.py, reused
    from FACTORY.CORE.exceptions) if any present entity is missing a
    required field -- never silently manufactures an invalid package."""
    extracted = extract(raw_document)
    normalized = normalize(extracted)
    validate(normalized)
    relationships = resolve_relationships(normalized)
    return build_canonical_package(normalized, relationships)


def manufacture_knowledge_packages(
    raw_documents: "Sequence[dict[str, Any] | None]",
) -> tuple[CanonicalKnowledgePackage, ...]:
    """MWO-LTSA-102B -- Batch entry point. Extends this pipeline (the
    single, canonical place CanonicalKnowledgePackage is ever built) rather
    than duplicating it: calls manufacture_knowledge_package() once per
    raw_document, in the given order, reusing every stage (Extraction/
    Normalization/Validation/Relationship-Resolution/Canonical-Object)
    exactly as the singular entry point already does -- no second
    implementation of any of those five stages exists here, and this
    function contains no business logic of its own beyond the loop.
    Fail-fast: raises ManufacturingValidationError on the first invalid
    raw_document, the same exception the singular entry point already
    raises -- never a partial/best-effort batch, never a silently-dropped
    invalid entry."""
    return tuple(manufacture_knowledge_package(raw_document) for raw_document in raw_documents)


# SQL-ready DTO stage. One dict per real canonical table (CANONICAL_SCHEMA.sql
# table names), each entry's own `raw` dict passed through verbatim (already
# normalized, already validated) -- this function builds dicts only, it
# executes no SQL and opens no connection (that remains the job of a
# *_db_upsert.py-style module, deliberately not built here per "No database
# writes"). `drawing` and `documents` share one output list
# ("seal_engineering_document") because they share one real target table --
# a Drawing is a seal_engineering_document row like any other, just one this
# pipeline happens to expose on its own `.drawing` field for convenience.
def to_sql_ready_dto(package: CanonicalKnowledgePackage) -> dict[str, Any]:
    engineering_documents = [dict(item.raw) for item in package.documents]
    if package.drawing is not None:
        engineering_documents = [dict(package.drawing.raw), *engineering_documents]

    dto: dict[str, Any] = {
        "ltsa_pumps": dict(package.pump.raw) if package.pump else None,
        "installation_report": dict(package.installation.raw) if package.installation else None,
        "seal_registry": dict(package.seal.raw) if package.seal else None,
        "seal_engineering_document": engineering_documents,
        "pm_occurrence": [dict(item.raw) for item in package.pm],
        "condition_monitoring_reading": [dict(item.raw) for item in package.cm],
        "cm_report": [dict(item.raw) for item in package.failure],
        "work_order": [dict(item.raw) for item in package.workorder],
    }
    return dto
