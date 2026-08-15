"""
PDF Import Foundation -- Parser / Normalizer / Field Mapper / Validation
stages that turn already-extracted PDF JSON into an API.import_validator.
ImportPackage. No OCR, no AI, no PDF-byte parsing anywhere in this module:
"Input is already extracted JSON" is the exact same boundary
knowledge_pipeline.py (MWO-LTSA-074) already draws for its own Extraction
stage -- reading a PDF/image and turning it into structured JSON is a
different, out-of-scope, upstream concern; this module starts one step
after that.

    Extracted JSON (already-structured, out-of-scope extraction)
      -> Parser        (extract_sections)     -- pull known top-level sections
      -> Normalizer     (normalize_sections)   -- whitespace/blank-value cleanup
      -> Field Mapper    (map_fields)           -- loose PDF-form labels -> real
                                                   canonical column names
      -> ImportPackage  (build_import_package / parse_pdf_extracted_json)

Scope, per this mission's own explicit "Read" list: Drawing, Installation,
Document only -- pumps and seals are never populated by this module
(ImportPackage.pumps/.seals always come back empty tuples; not this
pipeline's job, never fabricated). A Drawing is a document with
document_type='DRAWING' sharing the seal_engineering_document table, the
same "no separate drawing table exists" fact knowledge_dataclasses.py's
own header comment already established -- this module reuses that finding
rather than re-deriving it.

Reuse, not a duplicate engine:
  - Normalizer stage reuses knowledge_normalizers.normalize_dict/
    normalize_list/normalize_text (KNOWLEDGE-MANUFACTURING-PACK,
    MWO-LTSA-074) unmodified -- the exact same whitespace-collapse/
    blank-token discipline, imported via the same sys.path pattern
    import_execution_engine.py already uses to reach that pack at runtime.
  - Validation is NOT reimplemented here. This module's own pipeline stops
    at ImportPackage; API.import_validator.validate_import_package()
    (MWO-LTSA-076, reused unmodified) is the one place structural/
    relationship validation happens, including the MISSING_REQUIRED_FIELD
    check this mission's own "Missing field" test exercises. Callers chain
    validate_import_package(parse_pdf_extracted_json(raw)) themselves --
    exactly like knowledge_pipeline.manufacture_knowledge_package() calls
    its own validate() stage internally, except here the two stages are
    kept separately callable because import_validator.py's own contract is
    already "report errors, never raise" (see its own docstring), which
    this module must not contradict by also raising on the same condition.

Field Mapper design (disclosed, since no real "Extracted JSON" sample from
an actual upstream OCR/extraction tool exists anywhere in this repository
to reuse or reverse-engineer a label vocabulary from): rather than
hand-authoring a large table of speculative PDF form-label strings this
module has no evidence for, the mapper (a) passes through any key that is
already an exact, real canonical column name (installation_report /
seal_engineering_document, per CANONICAL_SCHEMA.sql, transcribed verbatim
below -- not invented), (b) matches any other key whose lowercased,
punctuation-collapsed form equals a canonical column's own
lowercased/punctuation-collapsed form (so "Installation Code",
"installation-code", "INSTALLATION_CODE" all resolve to the one real
`installation_code` column), and (c) additionally recognizes a small,
explicitly-listed set of common human-readable synonyms for the handful of
fields import_validator.py's own required/relationship logic actually
reads (installation_code/report_no/source_document_name/drawing_no/
seal_code/document_code/document_type/document_number/title). Any key
matching neither (a), (b), nor (c) is dropped, never guessed into a
fabricated column.

"Malformed PDF" (this mission's own test scenario, reused here as
"malformed Extracted JSON" per the "no OCR" boundary above): the Parser
stage raises FACTORY.CORE.exceptions.ManufacturingValidationError -- the
same one-line ValueError subclass knowledge_validators.py already reuses
for this codebase's structural-validation failures, not a new parallel
exception type -- when the top-level input is not a dict, or when a
present section's value is not the shape it must structurally be (a dict
for "installation"/"drawing", a list for "documents").
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.CORE.exceptions import ManufacturingValidationError  # noqa: E402

_KMP_PATH = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "KNOWLEDGE-MANUFACTURING-PACK"
if str(_KMP_PATH) not in sys.path:
    sys.path.insert(0, str(_KMP_PATH))

from knowledge_normalizers import normalize_dict, normalize_list  # noqa: E402

# CORE-SERVICES/ (this file's grandparent), so the sibling import_validator
# module is reachable as `API.import_validator` -- deliberately the dotted
# form, not a bare sibling import: import_router.py (CORE-SERVICES/
# BACKEND-API/routers/) and this module's own test file both already import
# it as `API.import_validator`, and Python treats a bare `import_validator`
# and a dotted `API.import_validator` as two DIFFERENT module objects with
# two different ImportPackage classes -- same file, but isinstance()/
# dataclass `==` would then silently fail across the two identities. Same
# sys.path base dependencies.py already establishes for every Gateway.
_CORE_SERVICES_PATH = Path(__file__).resolve().parents[1]
if str(_CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(_CORE_SERVICES_PATH))

from API.import_validator import ImportPackage  # noqa: E402

# --- Parser ------------------------------------------------------------------

_SINGULAR_SECTIONS = ("installation", "drawing")
_PLURAL_SECTIONS = ("documents",)


def extract_sections(raw_extracted: Any) -> dict[str, Any]:
    """Parser stage. Pulls out only the known top-level sections this
    pipeline understands ("installation", "drawing", "documents") -- same
    "never invent a section the input lacks" discipline as
    knowledge_pipeline.extract(). Raises ManufacturingValidationError for
    genuinely malformed input: not a dict at all, or a present section
    that is not the shape it must structurally be."""
    if not isinstance(raw_extracted, dict):
        raise ManufacturingValidationError(
            f"Extracted JSON must be a dict, got {type(raw_extracted).__name__}"
        )

    extracted: dict[str, Any] = {}
    for key in _SINGULAR_SECTIONS:
        value = raw_extracted.get(key)
        if value is not None and not isinstance(value, dict):
            raise ManufacturingValidationError(
                f"Extracted JSON section '{key}' must be a dict, got {type(value).__name__}"
            )
        extracted[key] = value
    for key in _PLURAL_SECTIONS:
        value = raw_extracted.get(key)
        if value is not None and not isinstance(value, list):
            raise ManufacturingValidationError(
                f"Extracted JSON section '{key}' must be a list, got {type(value).__name__}"
            )
        extracted[key] = value or []
    return extracted


# --- Normalizer ----------------------------------------------------------------


def normalize_sections(extracted: dict[str, Any]) -> dict[str, Any]:
    """Normalizer stage. Reuses knowledge_normalizers.normalize_dict/
    normalize_list unmodified -- no second whitespace/blank-token
    implementation."""
    normalized: dict[str, Any] = {}
    for key in _SINGULAR_SECTIONS:
        normalized[key] = normalize_dict(extracted.get(key)) or None
    for key in _PLURAL_SECTIONS:
        normalized[key] = normalize_list(extracted.get(key))
    return normalized


# --- Field Mapper --------------------------------------------------------------

# Real, canonical columns -- transcribed verbatim from
# PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql (seal_engineering_document
# / installation_report CREATE TABLE statements). created_at/updated_at are
# DB-managed, never import fields, and are excluded.

DOCUMENT_CANONICAL_FIELDS: tuple[str, ...] = (
    "document_code", "seal_code", "knowledge_source_id", "document_type",
    "document_number", "title", "revision", "issue_date", "manufacturer",
    "language", "description", "file_reference", "file_name", "file_format",
    "page_count", "status",
)

INSTALLATION_CANONICAL_FIELDS: tuple[str, ...] = (
    "installation_code", "report_no", "tso_no", "report_date", "customer",
    "address", "plant", "unit", "po_no", "packing_list_no", "location",
    "equipment_mfr", "model_type", "size", "configuration", "serial_no",
    "plant_equip_no", "pump_type", "shaft_speed", "rotation", "seal_manufacture",
    "seal_type", "seal_arrangement", "seal_size", "material_code", "drawing_no",
    "seal_location", "seal_code", "liquid", "temperature_range",
    "specific_gravity", "viscosity", "flash_point", "boiling_point",
    "freeze_point", "vapor_press", "discharge_press", "suction_press",
    "differential_press", "stuffing_box_press", "seal_press",
    "corrosion_erosion_by", "api_plan", "flush_liquid", "flush_pressure",
    "flush_temp", "flush_flowrate", "buffer_barrier_press", "buffer_barrier_fluid",
    "quench_fluid", "seal_chamber_shaft_inspection", "basic_seal_condition",
    "gland_condition", "sleeve_condition", "shaft_condition", "bearing_condition",
    "gasket_condition", "radial_bearing_no", "thrust_bearing_no", "summary_intro",
    "site_activity_intro", "site_activities", "bom_caption", "bill_of_material",
    "gland_observation_note", "gland_observation", "sleeve_observation_note",
    "sleeve_observation", "retainer_disc_observation_note",
    "retainer_disc_observation", "cartridge_drive_collar_observation_note",
    "cartridge_drive_collar_observation", "signatures", "source_document_name",
)

# Small, explicitly-disclosed synonym table -- only for the fields
# import_validator.py's own required-field/relationship logic actually
# reads (installation_code/report_no/source_document_name/drawing_no/
# seal_code, document_code/document_type/document_number/title). Every
# variant here is a common, human-plausible PDF form-label wording of a
# real column above, never an invented business field.
def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


_FIELD_SYNONYMS: dict[str, str] = {
    _normalize_key(raw_label): canonical
    for raw_label, canonical in {
        "installation no": "installation_code",
        "installation number": "installation_code",
        "report no": "report_no",
        "report number": "report_no",
        "source document": "source_document_name",
        "source document name": "source_document_name",
        "drawing no": "drawing_no",
        "drawing number": "drawing_no",
        "seal code": "seal_code",
        "doc code": "document_code",
        "document no": "document_code",
        "doc type": "document_type",
        "document title": "title",
    }.items()
}


def _map_record(record: dict[str, Any] | None, canonical_fields: tuple[str, ...]) -> dict[str, Any]:
    """Maps one record's raw keys onto real canonical column names.
    Unrecognized keys are dropped, never guessed into a fabricated
    column -- see this module's own header for why."""
    if not record:
        return {}

    canonical_by_normalized = {_normalize_key(field): field for field in canonical_fields}
    mapped: dict[str, Any] = {}
    for raw_key, value in record.items():
        if raw_key in canonical_fields:
            mapped[raw_key] = value
            continue
        normalized_key = _normalize_key(str(raw_key))
        canonical = canonical_by_normalized.get(normalized_key) or _FIELD_SYNONYMS.get(normalized_key)
        if canonical:
            mapped[canonical] = value
    return mapped


def map_fields(normalized: dict[str, Any]) -> dict[str, Any]:
    """Field Mapper stage. installation -> INSTALLATION_CANONICAL_FIELDS;
    drawing/documents -> DOCUMENT_CANONICAL_FIELDS (drawing and documents
    share one real target table, per knowledge_dataclasses.py's own
    finding -- reused here, not re-derived)."""
    return {
        "installation": _map_record(normalized.get("installation"), INSTALLATION_CANONICAL_FIELDS) or None,
        "drawing": _map_record(normalized.get("drawing"), DOCUMENT_CANONICAL_FIELDS) or None,
        "documents": [
            mapped
            for document in normalized.get("documents") or []
            if (mapped := _map_record(document, DOCUMENT_CANONICAL_FIELDS))
        ],
    }


# --- ImportPackage assembly ----------------------------------------------------


def build_import_package(mapped: dict[str, Any]) -> ImportPackage:
    """Assembles the final ImportPackage. pumps/seals are always empty --
    out of this mission's explicit scope, never fabricated. A mapped
    drawing (document_type='DRAWING') is prepended to documents, the same
    "drawing and documents share one real target table" merge
    knowledge_pipeline.to_sql_ready_dto() already performs for its own SQL
    DTO stage."""
    installation = mapped.get("installation")
    drawing = mapped.get("drawing")
    documents = list(mapped.get("documents") or [])
    if drawing:
        documents = [drawing, *documents]

    return ImportPackage(
        pumps=(),
        seals=(),
        installations=(installation,) if installation else (),
        documents=tuple(documents),
    )


def parse_pdf_extracted_json(raw_extracted: Any) -> ImportPackage:
    """The whole pipeline, one call: Parser -> Normalizer -> Field Mapper
    -> ImportPackage. Raises ManufacturingValidationError for malformed
    input (see extract_sections). Does not validate field completeness --
    chain API.import_validator.validate_import_package() over this
    function's own result for that (reused, not duplicated here)."""
    extracted = extract_sections(raw_extracted)
    normalized = normalize_sections(extracted)
    mapped = map_fields(normalized)
    return build_import_package(mapped)


__all__ = [
    "DOCUMENT_CANONICAL_FIELDS",
    "INSTALLATION_CANONICAL_FIELDS",
    "extract_sections",
    "normalize_sections",
    "map_fields",
    "build_import_package",
    "parse_pdf_extracted_json",
]
