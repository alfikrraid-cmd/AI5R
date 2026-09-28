"""Normalized data model for Engineering Drawing extraction (Drawing-R5B).

Mirrors models.py's own "any provider must produce this exact shape"
discipline (ExtractionResult/FieldValue) but with a richer, nested shape --
Drawing candidates (identity/revision/references/attributes/BOM) do not
fit a flat fields:dict[str, FieldValue] the way the Document Upload MVP's
21 fixed FIELD_NAMES do. This is a SPECIALIZATION of the same established
pattern for one new document domain, not a second generic framework.

STAGING EVIDENCE ONLY (Drawing-R5B's own explicit scope) -- every value
here is a CANDIDATE for human review, never written to any canonical
Drawing table directly. raw_value is the literal, verbatim source text
(e.g. '4.500"') -- never replaced by a normalized/converted value; a
normalized_value/value_numeric is only ever populated ALONGSIDE raw_value,
never instead of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

SCHEMA_VERSION = "drawing-extraction-v1"

# R5B Section 3 -- automated extraction supported now.
SUPPORTED_MIME_TYPES: tuple[str, ...] = ("application/pdf", "image/jpeg", "image/png", "image/webp")

# R5B Section 14 -- only warnings the extraction adapter itself can
# actually evidence are ever emitted; this list is closed so a caller can
# validate against it, but the ADAPTER never invents evidence-free values.
WARNING_CODES: tuple[str, ...] = (
    "DRAWING_NUMBER_NOT_FOUND",
    "REVISION_NOT_FOUND",
    "MANUFACTURER_NOT_FOUND",
    "AMBIGUOUS_IDENTITY",
    "AMBIGUOUS_UNIT",
    "UNRESOLVED_REFERENCE",
    "PARTIAL_BOM",
    "LOW_EXTRACTION_CONFIDENCE",
)

# R5B Section 9 -- open vocabulary (no CHECK/enum) of concepts a
# candidate MAY use, mirroring engineering_drawing_attribute's own
# deliberately-open attribute_concept column. Not exhaustive -- a
# provider may return any concept string; these are simply the ones
# R5/R5A already anticipated.
KNOWN_ATTRIBUTE_CONCEPTS: tuple[str, ...] = (
    "SEAL_TYPE", "SEAL_SIZE", "SHAFT_DIAMETER", "SLEEVE_DIAMETER",
    "GLAND_OD", "GLAND_THICKNESS", "PILOT_DIAMETER", "PCD", "SPIGOT",
    "THROTTLE_BORE", "FACE_MATERIAL", "SEAT_MATERIAL", "ELASTOMER",
    "METALLURGY", "PORT_SIZE", "PORT_TYPE", "PORT_FUNCTION", "API_PLAN",
)


def _confidence_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


@dataclass(frozen=True)
class IdentityFieldCandidate:
    """One identity fact (drawing_number/title/manufacturer/drawing_type).

    raw_value is the literal transcription; normalized_value is an
    optional, explicitly-separate cleaned-up form (e.g. whitespace
    trimmed) -- never a guess, never fabricated. None means genuinely
    not found/not legible -- never defaulted to an empty string.
    """

    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    source_location: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "source_location": self.source_location,
            "confidence": self.confidence,
        }

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "IdentityFieldCandidate":
        data = data or {}
        return IdentityFieldCandidate(
            raw_value=data.get("raw_value"),
            normalized_value=data.get("normalized_value"),
            source_location=data.get("source_location"),
            confidence=_confidence_or_none(data.get("confidence")),
        )


@dataclass(frozen=True)
class RevisionCandidate:
    revision: Optional[str] = None
    revision_date: Optional[str] = None
    source_location: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "revision_date": self.revision_date,
            "source_location": self.source_location,
            "confidence": self.confidence,
        }

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "RevisionCandidate":
        data = data or {}
        return RevisionCandidate(
            revision=data.get("revision"),
            revision_date=data.get("revision_date"),
            source_location=data.get("source_location"),
            confidence=_confidence_or_none(data.get("confidence")),
        )


@dataclass(frozen=True)
class ReferenceCandidate:
    """A candidate ASSET/SEAL/COMPONENT reference -- CANDIDATE ONLY.

    R5B never resolves or links these (Section 8's own explicit rule) --
    reference_type is free text describing what KIND of reference this
    is (e.g. 'EQUIPMENT_TAG', 'SEAL_TYPE', 'COMPONENT_IDENTITY',
    'MANUFACTURER_PART_NUMBER'), never a target_type/target_code pair.
    """

    reference_type: str
    raw_value: Optional[str] = None
    source_location: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_type": self.reference_type,
            "raw_value": self.raw_value,
            "source_location": self.source_location,
            "confidence": self.confidence,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ReferenceCandidate":
        return ReferenceCandidate(
            reference_type=data["reference_type"],
            raw_value=data.get("raw_value"),
            source_location=data.get("source_location"),
            confidence=_confidence_or_none(data.get("confidence")),
        )


@dataclass(frozen=True)
class AttributeCandidate:
    """One engineering fact candidate -- STAGING evidence only, never
    written to engineering_drawing_attribute directly (R5C/R5D's job).
    """

    concept: str
    source_label: Optional[str] = None
    raw_value: Optional[str] = None
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    source_location: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "source_label": self.source_label,
            "raw_value": self.raw_value,
            "value_numeric": self.value_numeric,
            "value_text": self.value_text,
            "unit": self.unit,
            "source_location": self.source_location,
            "confidence": self.confidence,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AttributeCandidate":
        return AttributeCandidate(
            concept=data["concept"],
            source_label=data.get("source_label"),
            raw_value=data.get("raw_value"),
            value_numeric=_confidence_or_none(data.get("value_numeric")),
            value_text=data.get("value_text"),
            unit=data.get("unit"),
            source_location=data.get("source_location"),
            confidence=_confidence_or_none(data.get("confidence")),
        )


@dataclass(frozen=True)
class BomLineCandidate:
    """One BOM line candidate -- source preserved first, resolution later
    (R5B Section 11's own explicit preference). GPN/manufacturer part
    number is NEVER fabricated -- None when not printed on the source."""

    item_position: Optional[str] = None
    description: Optional[str] = None
    quantity_raw: Optional[str] = None
    material_or_spec: Optional[str] = None
    gpn_or_part_number: Optional[str] = None
    source_location: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_position": self.item_position,
            "description": self.description,
            "quantity_raw": self.quantity_raw,
            "material_or_spec": self.material_or_spec,
            "gpn_or_part_number": self.gpn_or_part_number,
            "source_location": self.source_location,
            "confidence": self.confidence,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BomLineCandidate":
        return BomLineCandidate(
            item_position=data.get("item_position"),
            description=data.get("description"),
            quantity_raw=data.get("quantity_raw"),
            material_or_spec=data.get("material_or_spec"),
            gpn_or_part_number=data.get("gpn_or_part_number"),
            source_location=data.get("source_location"),
            confidence=_confidence_or_none(data.get("confidence")),
        )


@dataclass(frozen=True)
class DocumentIdentity:
    """Descriptive, non-authoritative facts about the FILE ITSELF --
    never an artifact_class guess (R5's own 'provenance determines
    authority, never inferred from extension/content' rule stays with
    the human upload-time decision, not this adapter)."""

    mime_type: str
    page_count: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {"mime_type": self.mime_type, "page_count": self.page_count}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DocumentIdentity":
        return DocumentIdentity(mime_type=data["mime_type"], page_count=data.get("page_count"))


@dataclass(frozen=True)
class DrawingIdentityCandidates:
    drawing_number: IdentityFieldCandidate = field(default_factory=IdentityFieldCandidate)
    title: IdentityFieldCandidate = field(default_factory=IdentityFieldCandidate)
    manufacturer: IdentityFieldCandidate = field(default_factory=IdentityFieldCandidate)
    drawing_type: IdentityFieldCandidate = field(default_factory=IdentityFieldCandidate)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drawing_number": self.drawing_number.to_dict(),
            "title": self.title.to_dict(),
            "manufacturer": self.manufacturer.to_dict(),
            "drawing_type": self.drawing_type.to_dict(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "DrawingIdentityCandidates":
        data = data or {}
        return DrawingIdentityCandidates(
            drawing_number=IdentityFieldCandidate.from_dict(data.get("drawing_number")),
            title=IdentityFieldCandidate.from_dict(data.get("title")),
            manufacturer=IdentityFieldCandidate.from_dict(data.get("manufacturer")),
            drawing_type=IdentityFieldCandidate.from_dict(data.get("drawing_type")),
        )


@dataclass(frozen=True)
class DrawingExtractionResult:
    schema_version: str
    document_identity: DocumentIdentity
    drawing_identity: DrawingIdentityCandidates
    revision_candidate: RevisionCandidate
    references: tuple[ReferenceCandidate, ...]
    attributes: tuple[AttributeCandidate, ...]
    bom_candidates: tuple[BomLineCandidate, ...]
    warnings: tuple[str, ...]
    ocr_text: str
    provider: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "document_identity": self.document_identity.to_dict(),
            "drawing_identity": self.drawing_identity.to_dict(),
            "revision_candidate": self.revision_candidate.to_dict(),
            "references": [r.to_dict() for r in self.references],
            "attributes": [a.to_dict() for a in self.attributes],
            "bom_candidates": [b.to_dict() for b in self.bom_candidates],
            "warnings": list(self.warnings),
            "ocr_text": self.ocr_text,
            "provider": self.provider,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DrawingExtractionResult":
        return DrawingExtractionResult(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            document_identity=DocumentIdentity.from_dict(data["document_identity"]),
            drawing_identity=DrawingIdentityCandidates.from_dict(data.get("drawing_identity")),
            revision_candidate=RevisionCandidate.from_dict(data.get("revision_candidate")),
            references=tuple(ReferenceCandidate.from_dict(r) for r in data.get("references", [])),
            attributes=tuple(AttributeCandidate.from_dict(a) for a in data.get("attributes", [])),
            bom_candidates=tuple(BomLineCandidate.from_dict(b) for b in data.get("bom_candidates", [])),
            warnings=tuple(data.get("warnings", [])),
            ocr_text=data.get("ocr_text", ""),
            provider=data.get("provider", "unknown"),
        )
