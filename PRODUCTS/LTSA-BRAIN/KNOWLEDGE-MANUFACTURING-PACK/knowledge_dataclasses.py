"""MWO-LTSA-074 -- LTSA Knowledge Manufacturing Engine, canonical dataclasses.

Nine immutable, deterministic entity objects plus the CanonicalKnowledgePackage
that aggregates them -- the pipeline's "Canonical Engineering Object" stage.

Design decision (disclosed): each entity carries a small set of strongly-typed
IDENTITY/RELATIONSHIP fields (the ones the relationship resolver and validators
actually need to reason about), plus a `raw` field holding the complete,
already-normalized extraction dict verbatim. This avoids hand-duplicating
every column of installation_report (~70 columns) into a second dataclass
definition that would need to be kept in lockstep with CANONICAL_SCHEMA.sql
forever -- the same "avoid storing duplicated facts" discipline this LTSA
product's own frontend mapping files (installationMapping.js etc.) already
follow. `raw` is never dropped, never re-derived, never fabricated -- it is
exactly the normalized input dict, wrapped for real immutability.

Real immutability, not just frozen-dataclass surface protection: `raw` is
stored as `types.MappingProxyType`, and every plural relationship is a
`tuple`, never a `list` -- `frozen=True` alone only blocks re-assigning a
field, not mutating a dict/list a field still points to.

Field provenance (evidence, not invention) -- every identity/relationship
field below is a real, already-established canonical column:
  Pump          -> ltsa_pumps (tag_number natural key, PUMP-FACTORY-PACK's
                   own PumpIdentityResolver confirms tag_number as the key)
  Installation  -> installation_report (installation_code PK, report_no
                   UNIQUE, plant_equip_no/drawing_no informal refs, seal_code
                   real nullable FK -- MWO-LTSA-060 schema, this session)
  Seal          -> seal_registry (seal_code PK)
  Drawing       -> seal_engineering_document WHERE document_type='DRAWING'
                   (confirmed the canonical drawing source by
                   LTSAKnowledgeService._build_drawings()'s own documented
                   rejection of pdf_document/document_field_extraction as
                   alternatives -- no separate "drawing" table exists)
  PM            -> pm_occurrence (pm_occurrence_code PK, asset_code informal
                   ref, pm_schedule_code required informal ref)
  CM            -> condition_monitoring_reading (the MEASUREMENT sense of
                   "CM" -- condition_monitoring_reading_code PK). Deliberately
                   NOT cm_report: DISCOVERY-LTSA-REPORT-001's own documented
                   "CM Is a Terminology Collision" finding is reused here,
                   this pipeline's "cm" output resolves to the measurement
                   table, and "failure" (below) resolves to the reactive one.
  Failure       -> cm_report (the CORRECTIVE MAINTENANCE / reactive-failure
                   sense of "CM" -- cm_report_code PK, work_order_code
                   informal ref, failure_date -- this session's own MWO-LTSA-
                   HOC-PM-CM extension).
  WorkOrder     -> work_order (work_order_code PK, asset_code informal ref)
  Document      -> seal_engineering_document (document_code PK, any
                   document_type -- Drawing is the one document_type='DRAWING'
                   row surfaced separately as `.drawing`, never duplicated
                   into `.documents` too)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class PumpObject:
    tag_number: str
    area: str | None = None
    pump_type: str | None = None
    seal_type: str | None = None
    drawing_ref: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class InstallationObject:
    installation_code: str
    report_no: str | None = None
    plant_equip_no: str | None = None
    drawing_no: str | None = None
    seal_code: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class SealObject:
    seal_code: str
    seal_name: str | None = None
    manufacturer: str | None = None
    shaft_size: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class DrawingObject:
    document_code: str
    seal_code: str | None = None
    document_number: str | None = None
    revision: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class PMObject:
    pm_occurrence_code: str
    asset_code: str | None = None
    pm_schedule_code: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class CMObject:
    """Condition Monitoring MEASUREMENT (condition_monitoring_reading), not
    the reactive-failure sense -- see module docstring's terminology-
    collision note."""

    condition_monitoring_reading_code: str
    asset_code: str | None = None
    condition_monitoring_schedule_code: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class FailureObject:
    """Corrective Maintenance / reactive failure (cm_report) -- see module
    docstring's terminology-collision note."""

    cm_report_code: str
    asset_code: str | None = None
    work_order_code: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class WorkOrderObject:
    work_order_code: str
    asset_code: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class DocumentObject:
    document_code: str
    seal_code: str | None = None
    document_type: str | None = None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class KnowledgeRelationshipSummary:
    """Mirrors FACTORY.RESOLUTION.relationship_resolver.RelationshipResolution's
    own (resolved, unresolved) shape (reused, not duplicated in spirit --
    this pipeline's resolver returns that exact type; this is the frozen,
    tuple-based form the immutable CanonicalKnowledgePackage stores)."""

    resolved: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CanonicalKnowledgePackage:
    """The pipeline's final "Canonical Engineering Object" -- one immutable,
    deterministic package per raw source document. Every plural field is a
    tuple (never a list); every optional singular field is None when the
    source document carries no evidence for it (never fabricated)."""

    pump: PumpObject | None = None
    installation: InstallationObject | None = None
    seal: SealObject | None = None
    drawing: DrawingObject | None = None
    pm: tuple[PMObject, ...] = ()
    cm: tuple[CMObject, ...] = ()
    failure: tuple[FailureObject, ...] = ()
    workorder: tuple[WorkOrderObject, ...] = ()
    documents: tuple[DocumentObject, ...] = ()
    relationships: KnowledgeRelationshipSummary = field(default_factory=KnowledgeRelationshipSummary)
