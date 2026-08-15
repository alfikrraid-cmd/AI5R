"""
MWO-LTSA-076 -- LTSA Data Import Foundation: deterministic validation of a
canonical import package (pumps/seals/installations/documents) before any
import execution ever happens. Validation only -- this module performs no
SQL, no gateway call, no HTTP request, and reads/writes no live system
state anywhere. It is a pure function of the JSON package handed to it.

Two, and only two, kinds of rule exist here, both explicitly grounded,
never invented:
  1. Structural rules -- a record is missing a column, or holds a value
     outside a closed vocabulary, that CANONICAL_SCHEMA.sql already
     enforces as NOT NULL / CHECK today (ltsa_pumps.tag_number/area,
     seal_registry.seal_code/seal_name, installation_report.
     installation_code/report_no/source_document_name,
     seal_engineering_document.document_code/seal_code/document_type/
     title, and document_type's own 7-value CHECK constraint). These are
     ImportError -- a record this shape can never be inserted, regardless
     of what else exists.
  2. Within-package relationship rules -- does a reference one record
     makes (installation.plant_equip_no -> pump.tag_number,
     installation.seal_code / document.seal_code -> seal.seal_code,
     installation.drawing_no -> a DRAWING-type document.document_number,
     and the inverse "does this seal have any document at all") resolve
     to another record in the SAME package. These are ImportWarning, not
     ImportError -- the referenced record may already exist in the live
     system (a fact this module has no SQL/API access to confirm), so an
     unresolved within-package reference is a real, disclosed
     possibility, never an assumed failure.

Reuse, not a duplicate engine: the four entity shapes read here
(tag_number/area/..., seal_code/seal_name/..., installation_code/
report_no/plant_equip_no/seal_code/drawing_no/..., document_code/
seal_code/document_type/document_number/title/...) are exactly the
snake_case "Raw Backend" shapes pumpMapping.js/sealMapping.js/
installationMapping.js/documentMapping.js already map from -- no new
field is read, no new vocabulary is invented. Pump Lifecycle, Timeline,
Recommendation, Pump Workspace, and Seal Workspace are untouched (out of
this MWO's explicit scope) and this module imports nothing from any of
them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DOCUMENT_TYPES = (
    "DRAWING",
    "DATASHEET",
    "INSTALLATION_GUIDE",
    "INSPECTION_SHEET",
    "MAINTENANCE_MANUAL",
    "SERVICE_BULLETIN",
    "ENGINEERING_SPECIFICATION",
)


# --- Input: the canonical import package -----------------------------------


@dataclass(frozen=True, slots=True)
class ImportPackage:
    """The parsed, canonical JSON input -- one list per entity type, each
    entry a raw snake_case record in the exact shape the real gateways
    already return (never reshaped, never renamed)."""

    pumps: tuple[dict[str, Any], ...]
    seals: tuple[dict[str, Any], ...]
    installations: tuple[dict[str, Any], ...]
    documents: tuple[dict[str, Any], ...]


def parse_import_package(data: dict[str, Any] | None) -> ImportPackage:
    """Parses a raw canonical JSON dict into an ImportPackage. Missing
    entity lists default to an empty tuple -- never fabricated, and never
    an error by themselves (an import package validating only pumps, for
    example, is legitimate)."""
    data = data or {}
    return ImportPackage(
        pumps=tuple(data.get("pumps") or ()),
        seals=tuple(data.get("seals") or ()),
        installations=tuple(data.get("installations") or ()),
        documents=tuple(data.get("documents") or ()),
    )


# --- Output: validation findings --------------------------------------------


# CAUTION -- this dataclass's name shadows the Python builtin
# `ImportError` exception. Named exactly this way because this MWO's own
# "Produce:" list names it verbatim (ImportSummary/ImportError/
# ImportWarning/ImportRelationship) -- not an accident, and not silently
# avoided by renaming it, per this Constitution's own rule that Blueprint/
# MWO naming may only change through the Chief Architect, never
# unilaterally. Real, disclosed risk: any file that does
# `from .import_validator import ImportError` (or `import *`) and also
# has an unrelated `except ImportError:` (the common "optional dependency"
# Python idiom) elsewhere in that same file will have that except clause
# silently broken (catching a non-Exception class raises TypeError at the
# except site). Mitigation: this module itself never uses the builtin
# ImportError, and this dataclass is never re-exported via `import *`
# from anywhere else in this codebase -- callers should import it
# qualified (`from .import_validator import ImportError as
# ImportValidationError`, or `import_validator.ImportError`) rather than
# bare, exactly as this module's own test file does.
@dataclass(frozen=True, slots=True)
class ImportError:
    """A structural or duplicate-key problem that makes a record
    unimportable regardless of what else is in the package or already in
    the live system."""

    code: str
    entity_type: str
    entity_id: str | None
    field: str | None
    message: str


@dataclass(frozen=True, slots=True)
class ImportWarning:
    """A within-package reference that did not resolve to another record
    in this same package. Not necessarily wrong -- the referenced record
    may already exist live; this module has no SQL/API access to check."""

    code: str
    entity_type: str
    entity_id: str | None
    field: str | None
    message: str


@dataclass(frozen=True, slots=True)
class ImportRelationship:
    """One cross-entity reference found in the package, resolved or not.
    The full set (not just the unresolved ones) is returned, so a caller
    can audit the whole within-package relationship graph, not only its
    gaps."""

    from_entity_type: str
    from_entity_id: str
    field: str
    to_entity_type: str
    to_entity_id: str
    resolved: bool


@dataclass(frozen=True, slots=True)
class ImportSummary:
    """Counts only -- every number here is len() of a real list this
    module already built, never a separately-tracked/duplicated count."""

    pump_count: int
    seal_count: int
    installation_count: int
    document_count: int
    error_count: int
    warning_count: int
    relationship_count: int
    unresolved_relationship_count: int
    is_valid: bool


@dataclass(frozen=True, slots=True)
class ValidatedImportPackage:
    """The full validation result: the package's own counts, every error/
    warning/relationship found, and a summary. No SQL was run, no record
    was written -- this is a report, not an import."""

    summary: ImportSummary
    errors: tuple[ImportError, ...]
    warnings: tuple[ImportWarning, ...]
    relationships: tuple[ImportRelationship, ...]


# --- Validator ---------------------------------------------------------------


def validate_import_package(package: ImportPackage) -> ValidatedImportPackage:
    errors: list[ImportError] = []
    warnings: list[ImportWarning] = []

    errors.extend(_validate_pumps(package.pumps))
    errors.extend(_validate_seals(package.seals))
    errors.extend(_validate_installations(package.installations))
    errors.extend(_validate_documents(package.documents))

    relationships = _build_relationships(package)
    warnings.extend(_warnings_for_unresolved(relationships))

    summary = ImportSummary(
        pump_count=len(package.pumps),
        seal_count=len(package.seals),
        installation_count=len(package.installations),
        document_count=len(package.documents),
        error_count=len(errors),
        warning_count=len(warnings),
        relationship_count=len(relationships),
        unresolved_relationship_count=sum(1 for r in relationships if not r.resolved),
        is_valid=len(errors) == 0,
    )

    return ValidatedImportPackage(
        summary=summary,
        errors=tuple(errors),
        warnings=tuple(warnings),
        relationships=tuple(relationships),
    )


# --- Structural validation (grounded in CANONICAL_SCHEMA.sql's own NOT NULL/CHECK) ---


def _require(record: dict[str, Any], field: str, entity_type: str, entity_id: str | None) -> ImportError | None:
    value = record.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        return ImportError(
            code="MISSING_REQUIRED_FIELD",
            entity_type=entity_type,
            entity_id=entity_id,
            field=field,
            message=f"{entity_type} record is missing required field '{field}'",
        )
    return None


def _validate_pumps(pumps: tuple[dict[str, Any], ...]) -> list[ImportError]:
    errors: list[ImportError] = []
    seen: dict[str, int] = {}
    for pump in pumps:
        tag_number = pump.get("tag_number")
        for field in ("tag_number", "area"):
            if (err := _require(pump, field, "pump", tag_number)) is not None:
                errors.append(err)
        if tag_number:
            errors.extend(_duplicate_error("pump", "tag_number", tag_number, seen))
    return errors


def _validate_seals(seals: tuple[dict[str, Any], ...]) -> list[ImportError]:
    errors: list[ImportError] = []
    seen: dict[str, int] = {}
    for seal in seals:
        seal_code = seal.get("seal_code")
        for field in ("seal_code", "seal_name"):
            if (err := _require(seal, field, "seal", seal_code)) is not None:
                errors.append(err)
        if seal_code:
            errors.extend(_duplicate_error("seal", "seal_code", seal_code, seen))
    return errors


def _validate_installations(installations: tuple[dict[str, Any], ...]) -> list[ImportError]:
    errors: list[ImportError] = []
    seen: dict[str, int] = {}
    for installation in installations:
        installation_code = installation.get("installation_code")
        for field in ("installation_code", "report_no", "source_document_name"):
            if (err := _require(installation, field, "installation", installation_code)) is not None:
                errors.append(err)
        if installation_code:
            errors.extend(_duplicate_error("installation", "installation_code", installation_code, seen))
    return errors


def _validate_documents(documents: tuple[dict[str, Any], ...]) -> list[ImportError]:
    errors: list[ImportError] = []
    seen: dict[str, int] = {}
    for document in documents:
        document_code = document.get("document_code")
        for field in ("document_code", "seal_code", "document_type", "title"):
            if (err := _require(document, field, "document", document_code)) is not None:
                errors.append(err)
        if document_code:
            errors.extend(_duplicate_error("document", "document_code", document_code, seen))

        document_type = document.get("document_type")
        if document_type is not None and document_type not in DOCUMENT_TYPES:
            errors.append(
                ImportError(
                    code="INVALID_DOCUMENT_TYPE",
                    entity_type="document",
                    entity_id=document_code,
                    field="document_type",
                    message=f"document_type '{document_type}' is not one of {DOCUMENT_TYPES}",
                )
            )
    return errors


def _duplicate_error(entity_type: str, field: str, value: str, seen: dict[str, int]) -> list[ImportError]:
    seen[value] = seen.get(value, 0) + 1
    if seen[value] > 1:
        return [
            ImportError(
                code=f"DUPLICATE_{entity_type.upper()}",
                entity_type=entity_type,
                entity_id=value,
                field=field,
                message=f"Duplicate {entity_type} in import package: {field}='{value}' appears more than once",
            )
        ]
    return []


# --- Relationship / missing-reference validation (within-package only) -----


def _build_relationships(package: ImportPackage) -> list[ImportRelationship]:
    pump_tags = {p.get("tag_number") for p in package.pumps if p.get("tag_number")}
    seal_codes = {s.get("seal_code") for s in package.seals if s.get("seal_code")}
    drawing_numbers = {
        d.get("document_number")
        for d in package.documents
        if d.get("document_type") == "DRAWING" and d.get("document_number")
    }
    documented_seal_codes = {d.get("seal_code") for d in package.documents if d.get("seal_code")}

    relationships: list[ImportRelationship] = []

    # Missing Pump: installation.plant_equip_no -> pump.tag_number
    for installation in package.installations:
        installation_code = installation.get("installation_code") or "unknown"
        plant_equip_no = installation.get("plant_equip_no")
        if plant_equip_no:
            relationships.append(
                ImportRelationship(
                    from_entity_type="installation",
                    from_entity_id=installation_code,
                    field="plant_equip_no",
                    to_entity_type="pump",
                    to_entity_id=plant_equip_no,
                    resolved=plant_equip_no in pump_tags,
                )
            )

        # Missing Seal (installation side): installation.seal_code -> seal.seal_code
        seal_code = installation.get("seal_code")
        if seal_code:
            relationships.append(
                ImportRelationship(
                    from_entity_type="installation",
                    from_entity_id=installation_code,
                    field="seal_code",
                    to_entity_type="seal",
                    to_entity_id=seal_code,
                    resolved=seal_code in seal_codes,
                )
            )

        # Missing Drawing: installation.drawing_no -> a DRAWING document.document_number
        drawing_no = installation.get("drawing_no")
        if drawing_no:
            relationships.append(
                ImportRelationship(
                    from_entity_type="installation",
                    from_entity_id=installation_code,
                    field="drawing_no",
                    to_entity_type="drawing",
                    to_entity_id=drawing_no,
                    resolved=drawing_no in drawing_numbers,
                )
            )

    # Missing Seal (document side): document.seal_code -> seal.seal_code
    for document in package.documents:
        document_code = document.get("document_code") or "unknown"
        seal_code = document.get("seal_code")
        if seal_code:
            relationships.append(
                ImportRelationship(
                    from_entity_type="document",
                    from_entity_id=document_code,
                    field="seal_code",
                    to_entity_type="seal",
                    to_entity_id=seal_code,
                    resolved=seal_code in seal_codes,
                )
            )

    # Missing Document: does this seal have at least one document in the
    # package referencing it? The inverse direction from every other
    # relationship above (seal -> document, not document -> seal).
    for seal in package.seals:
        seal_code = seal.get("seal_code")
        if seal_code:
            relationships.append(
                ImportRelationship(
                    from_entity_type="seal",
                    from_entity_id=seal_code,
                    field="documents",
                    to_entity_type="document",
                    to_entity_id=seal_code,
                    resolved=seal_code in documented_seal_codes,
                )
            )

    return relationships


_MISSING_CODE_BY_TARGET = {
    "pump": "MISSING_PUMP",
    "seal": "MISSING_SEAL",
    "drawing": "MISSING_DRAWING",
    "document": "MISSING_DOCUMENT",
}


def _warnings_for_unresolved(relationships: list[ImportRelationship]) -> list[ImportWarning]:
    warnings: list[ImportWarning] = []
    for relationship in relationships:
        if relationship.resolved:
            continue
        code = _MISSING_CODE_BY_TARGET.get(relationship.to_entity_type, "MISSING_REFERENCE")
        if relationship.to_entity_type == "document":
            message = (
                f"seal '{relationship.from_entity_id}' has no document in this import package "
                f"referencing it (may already exist live -- not checked)"
            )
        else:
            message = (
                f"{relationship.from_entity_type} '{relationship.from_entity_id}' references "
                f"{relationship.to_entity_type} '{relationship.to_entity_id}' via '{relationship.field}', "
                f"which is not present in this import package (may already exist live -- not checked)"
            )
        warnings.append(
            ImportWarning(
                code=code,
                entity_type=relationship.from_entity_type,
                entity_id=relationship.from_entity_id,
                field=relationship.field,
                message=message,
            )
        )
    return warnings


__all__ = [
    "DOCUMENT_TYPES",
    "ImportPackage",
    "ImportError",
    "ImportWarning",
    "ImportRelationship",
    "ImportSummary",
    "ValidatedImportPackage",
    "parse_import_package",
    "validate_import_package",
]
