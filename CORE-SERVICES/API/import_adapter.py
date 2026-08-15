"""
MWO-LTSA-089 -- Universal Import Adapter. Every real import source
(JSON, PDF, Excel, Folder, ZIP) must eventually become exactly one
canonical API.import_validator.ImportPackage. The Import Workspace
(AI5R-STUDIO/dashboard/.../ImportWorkspace.jsx, untouched by this MWO)
never learns which adapter ran -- it only ever receives an ImportPackage,
via the five Import API endpoints (import_router.py, also untouched).

Adaptation only. This module performs NO validation (API.import_validator.
validate_import_package), NO conflict resolution (API.conflict_resolution),
and NO execution (API.import_execution_engine) -- all three stages are
reused unmodified, exactly as pdf_import_parser.py's own docstring already
requires: "Callers chain validate_import_package(parse_...(raw)) themselves."
This module produces the ImportPackage those stages consume; it never
calls them.

Reuse, not a duplicate engine:
  - ImportPackage / parse_import_package() -- reused unmodified from
    API.import_validator (this directory, MWO-LTSA-076). JsonImportAdapter
    delegates to parse_import_package() verbatim; no second JSON-to-
    ImportPackage mapping exists anywhere in this module.
  - parse_pdf_extracted_json() -- reused unmodified from
    API.pdf_import_parser (this directory). PdfImportAdapter delegates to
    it verbatim; no second PDF/Extracted-JSON field mapper exists here.
  - ManufacturingValidationError -- reused unmodified from
    FACTORY.CORE.exceptions (AI5R-SDK), the one exception type this whole
    engineering line already uses for "this input cannot become a valid
    manufacturing artifact" (pdf_import_parser.py's own Parser stage
    raises the same class for malformed Extracted JSON). An unsupported/
    undetectable import source is the same category of failure one level
    earlier -- reused here, not a new parallel exception type.
  - Both cross-module imports below use the dotted `API.<module>` form,
    matching import_session.py/import_execution_engine.py/conflict_
    resolution.py/pdf_import_parser.py's own already-documented reason:
    a bare `import import_validator` and the dotted `API.import_validator`
    are two different module objects with two different ImportPackage
    classes, silently breaking isinstance()/dataclass `==` across the two
    identities.

PDF adapter design (disclosed, not invented): pdf_import_parser.py's own
header draws a hard, explicit boundary -- "No OCR, no AI, no PDF-byte
parsing anywhere in this module: Input is already extracted JSON" -- and
no PDF-byte/OCR extraction library (pdfplumber/PyPDF2/pypdf/fitz/pdfminer)
exists anywhere in this repository to reuse for turning real PDF bytes
into that JSON (confirmed by repository-wide search before writing this
adapter). This mission's own rule is "Reuse pdf_import_parser.py. Do NOT
duplicate parser" -- writing a new PDF-byte reader here would be exactly
that duplication (a second, competing "how do we get from PDF to
structured data" engine) plus new, out-of-scope OCR/AI machinery this
Constitution's Golden Rule 4 (deterministic, no AI, no guessing)
forbids outright. PdfImportAdapter therefore reads the file at file_path
as UTF-8 JSON text -- the exact "already extracted JSON" artifact
pdf_import_parser.py's own contract already requires -- the identical
read-then-delegate shape JsonImportAdapter uses, and delegates to
parse_pdf_extracted_json() unmodified. Real PDF-byte/OCR extraction
remains the disclosed, out-of-scope, upstream concern pdf_import_parser.py
already named; this adapter does not invent it.

Excel adapter design (MWO-LTSA-090, disclosed, not invented): the one raw
"open .xlsx/.xls and hand back worksheet rows" step is reused verbatim from
AI5R-SDK/ENTERPRISE_DATA_ENGINE/excel_reader.py::ExcelReader (openpyxl for
.xlsx, xlrd for .xls) -- no second Excel byte-reader is written here.
ENTERPRISE_DATA_ENGINE.column_mapper.ColumnMapper is deliberately NOT
reused for the canonical-field-mapping step: that engine assigns generic,
confidence-scored semantic labels (Email/Phone/Amount/Identifier/...) for
arbitrary enterprise datasets -- a different target vocabulary than this
ImportPackage's four canonical entities, and its <1.0-confidence fuzzy
alias matching is exactly the kind of guessing this mission's own "Never
invent mappings" rule and Golden Rule 4 (deterministic) forbid. Field
mapping here instead mirrors PdfImportAdapter's own discipline: exact
canonical column name match only (case-insensitive, punctuation-collapsed),
transcribed verbatim from CANONICAL_SCHEMA.sql -- no synonym table (unlike
PdfImportAdapter's own small, PDF-specific synonym list: this mission's
requirements say "case-insensitive mapping", nothing about synonyms, so
none are invented). MWO-LTSA-HOC-PM-CM's own Excel ingestion pipeline
(PRODUCTS/LTSA-BRAIN/INGESTION/ltsa_hoc_pm_cm_ingestion.py) is a different,
PM/CM-workbook-specific shape, not this ImportPackage contract, so it is
not reused/duplicated here either.

Detection is extension-only (never filename guessing), against the real
path's `Path.suffix`, case-insensitive. FolderImportAdapter is the one
exception with no extension at all (`is_dir()`), and is checked first in
UniversalImportAdapter's detection order so a directory with a dotted name
(e.g. "archive.zip/") is never misrouted to an extension-based adapter.

--------------------------------------------------------------------------
MWO-LTSA-091 -- Folder Batch Import (this revision)
--------------------------------------------------------------------------
Implements FolderImportAdapter.parse(), previously `raise
NotImplementedError("Folder adapter not implemented yet.")`. Flow, per
this MWO's own explicit diagram: Folder -> scan files ->
UniversalImportAdapter.parse() -> tuple[ImportPackage]. Recursive,
ignores unsupported files, stable deterministic ordering, never
validates/executes/detects conflicts -- the same "adaptation only"
discipline every other adapter in this module already follows.

Return-type note (disclosed, not accidental): every other
ImportAdapter.parse() returns exactly one ImportPackage (one file -> one
package). A folder legitimately contains zero-to-many importable files,
so this override's real return type is tuple[ImportPackage, ...] instead
of the ABC's single-ImportPackage type hint -- a deliberate divergence
this MWO's own required "Output: tuple[ImportPackage]" leaves no
alternative to. Nothing about ImportAdapter or UniversalImportAdapter
changes to accommodate this: neither class's code is touched, and
UniversalImportAdapter.parse(some_directory) still does exactly what it
always did -- detect FolderImportAdapter, call its parse(), return
whatever comes back, unmodified.

Reuse, not a duplicate adapter: `_scan_folder`'s own notion of "supported
file" is UniversalImportAdapter.detect_adapter() itself (reused, not a
second/parallel extension list) -- a file is scanned in only if
UniversalImportAdapter already recognizes its extension AND the adapter
that recognizes it has a genuinely working parse() today. ZipImportAdapter
IS detected (its extension is real and recognized) but its own parse()
unconditionally raises NotImplementedError (MWO-LTSA-089's own disclosed
scope) -- an adapter that cannot yet parse anything is not a "supported
file" for a batch scan, so .zip files are ignored here too, same as any
other unrecognized extension. Every discovered supported file is still
handed to the real UniversalImportAdapter.parse() -- JsonImportAdapter/
PdfImportAdapter/ExcelImportAdapter are never re-invoked directly, only
through that one, same factory entry point every other caller already
uses.
"""

from __future__ import annotations

import json
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from ENTERPRISE_DATA_ENGINE import ExcelReader, SourceDescriptor  # noqa: E402
from FACTORY.CORE.exceptions import ManufacturingValidationError  # noqa: E402

_KMP_PATH = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "KNOWLEDGE-MANUFACTURING-PACK"
if str(_KMP_PATH) not in sys.path:
    sys.path.insert(0, str(_KMP_PATH))

from knowledge_normalizers import normalize_dict  # noqa: E402

_CORE_SERVICES_PATH = Path(__file__).resolve().parents[1]
if str(_CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(_CORE_SERVICES_PATH))

from API.import_validator import ImportPackage, parse_import_package  # noqa: E402
from API.pdf_import_parser import DOCUMENT_CANONICAL_FIELDS, INSTALLATION_CANONICAL_FIELDS, parse_pdf_extracted_json  # noqa: E402


# --- ImportAdapter (ABC) ------------------------------------------------------


class ImportAdapter(ABC):
    """One adapter per real import source. detect() decides whether this
    adapter owns a given file_path; parse() turns that file into the one
    canonical ImportPackage. Stateless by design (no adapter holds any
    instance data) -- instantiated once per parse() call by
    UniversalImportAdapter so the ABC's abstractmethod contract is
    actually enforced (a concrete subclass missing parse()/
    supported_extensions() fails at instantiation, not silently later)."""

    @staticmethod
    @abstractmethod
    def supported_extensions() -> tuple[str, ...]:
        """Lowercase, dot-prefixed extensions this adapter owns, e.g.
        ('.json',). Empty tuple for the one adapter detected by shape, not
        extension (FolderImportAdapter)."""

    @classmethod
    def detect(cls, file_path: Path) -> bool:
        """Extension-only detection -- never filename guessing. Overridden
        by FolderImportAdapter, which has no extension to match."""
        return Path(file_path).suffix.lower() in cls.supported_extensions()

    @abstractmethod
    def parse(self, file_path: Path) -> ImportPackage:
        """Turns file_path into the one canonical ImportPackage. No
        validation, no conflict check, no execution -- those stages are
        reused unmodified downstream, never re-implemented or re-invoked
        here."""


# --- Excel canonical field mapping (MWO-LTSA-090) -----------------------------

# Real, canonical columns -- transcribed verbatim from
# PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql (ltsa_pumps / public.
# seal_registry CREATE TABLE statements). id/created_at/updated_at are
# DB-managed, never import fields, and are excluded -- the same exclusion
# pdf_import_parser.py's own INSTALLATION_CANONICAL_FIELDS/
# DOCUMENT_CANONICAL_FIELDS already apply, reused unmodified below rather
# than re-transcribed.

PUMP_CANONICAL_FIELDS: tuple[str, ...] = (
    "tag_number", "area", "location", "pump_type", "api_plan", "seal_type",
    "status", "manufacturer", "model", "drawing_ref", "notes", "name",
    "criticality",
)

SEAL_CANONICAL_FIELDS: tuple[str, ...] = (
    "seal_code", "seal_name", "manufacturer", "model", "shaft_size",
    "material", "temperature_limit", "pressure_limit", "status",
)

_CANONICAL_FIELDS_BY_ENTITY: dict[str, tuple[str, ...]] = {
    "pumps": PUMP_CANONICAL_FIELDS,
    "seals": SEAL_CANONICAL_FIELDS,
    "installations": INSTALLATION_CANONICAL_FIELDS,
    "documents": DOCUMENT_CANONICAL_FIELDS,
}

# Sheet name -> ImportPackage bucket. Singular and plural are the only two
# forms recognized -- both are already the real, canonical entity/field
# names this whole Import pipeline uses everywhere (ImportPackage.pumps/
# seals/installations/documents, import_validator's own entity_type
# strings "pump"/"seal"/"installation"/"document") -- not new vocabulary,
# and no other synonym is guessed. Every other sheet name is unknown and
# ignored, per this mission's own "Ignore unknown sheets" rule.
_SHEET_NAME_TO_ENTITY: dict[str, str] = {
    "pump": "pumps", "pumps": "pumps",
    # MWO-LTSA-DATA-IMPORT-UI-001A -- "Master Pump" is the real sheet name
    # in the RU II Pump Master acceptance workbook
    # (LTSA_RU_II_Master_Pump_Canonical.xlsx, confirmed by direct
    # inspection: sheets are "Master Pump"/"Summary"/"Validation Queue").
    # Still the same canonical "pumps" bucket -- not a new entity, not a
    # new mapping vocabulary, just one more recognized spelling of the
    # entity this adapter already handles.
    "master_pump": "pumps",  # normalized form of "Master Pump" -- lookups are always post-_normalize_header
    "seal": "seals", "seals": "seals",
    "installation": "installations", "installations": "installations",
    "document": "documents", "documents": "documents",
}


def _normalize_header(value: Any) -> str:
    """Case-insensitive, punctuation-collapsed normalization -- the same
    idiom pdf_import_parser.py's own _normalize_key already established
    for this exact "loose label -> canonical name" comparison, reused here
    at the same shape rather than re-derived. Used for both sheet names and
    column headers."""
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _map_row(headers: tuple[Any, ...], row: tuple[Any, ...], canonical_fields: tuple[str, ...]) -> dict[str, Any]:
    """Maps one worksheet data row onto real canonical column names, by
    header, case-insensitively. Unrecognized columns are dropped, never
    guessed into a fabricated field ("Ignore unknown columns"). Reuses
    knowledge_normalizers.normalize_dict for the same whitespace/blank-
    token cleanup pdf_import_parser.py's own Normalizer stage already
    applies -- a row whose every recognized cell is blank collapses to {}
    and is skipped by the caller, never fabricated as an empty record."""
    canonical_by_normalized = {_normalize_header(field): field for field in canonical_fields}
    raw_record: dict[str, Any] = {}
    for header, value in zip(headers, row):
        canonical = canonical_by_normalized.get(_normalize_header(header))
        if canonical:
            raw_record[canonical] = value
    record = normalize_dict(raw_record)
    return record if any(value is not None for value in record.values()) else {}


# --- Concrete adapters ---------------------------------------------------------


class JsonImportAdapter(ImportAdapter):
    """Reuses API.import_validator.parse_import_package() unmodified -- the
    file's JSON content is already the canonical
    {pumps, seals, installations, documents} shape."""

    @staticmethod
    def supported_extensions() -> tuple[str, ...]:
        return (".json",)

    def parse(self, file_path: Path) -> ImportPackage:
        data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return parse_import_package(data)


class PdfImportAdapter(ImportAdapter):
    """Reuses API.pdf_import_parser.parse_pdf_extracted_json() unmodified.
    See this module's own header for why the file is read as JSON text,
    not raw PDF bytes -- pdf_import_parser.py's own boundary, not invented
    here."""

    @staticmethod
    def supported_extensions() -> tuple[str, ...]:
        return (".pdf",)

    def parse(self, file_path: Path) -> ImportPackage:
        raw_extracted = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return parse_pdf_extracted_json(raw_extracted)


class ExcelImportAdapter(ImportAdapter):
    """Workbook -> detect sheets -> map canonical fields -> ImportPackage.
    See this module's own header ("Excel adapter design") for the full
    reuse rationale: ExcelReader (ENTERPRISE_DATA_ENGINE, unmodified) does
    the one mechanical "open the workbook, hand back raw worksheet rows"
    step; canonical field mapping is this adapter's own small, deterministic,
    exact-match-only logic (_map_row/_normalize_header above), never
    ColumnMapper's fuzzy/confidence-scored engine. No validation, no
    conflict check, no execution -- adaptation only, same as every other
    adapter in this module."""

    @staticmethod
    def supported_extensions() -> tuple[str, ...]:
        return (".xlsx", ".xls")

    def parse(self, file_path: Path) -> ImportPackage:
        path = Path(file_path)
        try:
            dataset = ExcelReader().read(
                SourceDescriptor(source_id=str(path), reader_name="excel", location=str(path))
            )
        except Exception as error:
            raise ManufacturingValidationError(
                f"Unreadable/corrupt workbook '{path}': {error}"
            ) from error

        buckets: dict[str, list[dict[str, Any]]] = {"pumps": [], "seals": [], "installations": [], "documents": []}
        for worksheet in dataset.data:
            entity_key = _SHEET_NAME_TO_ENTITY.get(_normalize_header(worksheet["name"]))
            if entity_key is None:
                continue  # Ignore unknown sheets.

            rows = worksheet["rows"]
            if not rows:
                continue
            headers, *data_rows = rows

            canonical_fields = _CANONICAL_FIELDS_BY_ENTITY[entity_key]
            for raw_row in data_rows:
                record = _map_row(headers, raw_row, canonical_fields)
                if record:
                    buckets[entity_key].append(record)

        return ImportPackage(
            pumps=tuple(buckets["pumps"]),
            seals=tuple(buckets["seals"]),
            installations=tuple(buckets["installations"]),
            documents=tuple(buckets["documents"]),
        )


class ZipImportAdapter(ImportAdapter):
    """Detection only. No unpacking -- per this mission's explicit scope."""

    @staticmethod
    def supported_extensions() -> tuple[str, ...]:
        return (".zip",)

    def parse(self, file_path: Path) -> ImportPackage:
        raise NotImplementedError("ZIP adapter not implemented yet.")


# --- Folder batch scan (MWO-LTSA-091) -------------------------------------


def _is_batch_supported_file(path: Path) -> bool:
    """True only for a real file whose extension UniversalImportAdapter
    already recognizes with a genuinely working parser. Reuses
    detect_adapter() itself -- see this module's own "MWO-LTSA-091" header
    section for why .zip (detected, but its parse() unconditionally raises
    NotImplementedError) is excluded the same way an unrecognized
    extension is. A directory is never itself "a file" here -- the
    recursive walk below descends into it instead of treating it as one
    adapter-detected unit."""
    if not path.is_file():
        return False
    try:
        adapter_cls = UniversalImportAdapter.detect_adapter(path)
    except ManufacturingValidationError:
        return False
    return adapter_cls not in (FolderImportAdapter, ZipImportAdapter)


def _scan_folder(folder_path: Path) -> tuple[Path, ...]:
    """Recursive scan, per this mission's own explicit rule. Stable,
    deterministic ordering: every discovered supported file, sorted by its
    path relative to folder_path in POSIX form, case-insensitively -- the
    same ordering regardless of OS or filesystem enumeration order.
    Raises ManufacturingValidationError for an unreadable folder (not a
    directory at all, or a genuine OS-level read failure while walking
    it) -- this mission's own one named error case."""
    if not folder_path.is_dir():
        raise ManufacturingValidationError(f"Unreadable folder: '{folder_path}' is not a directory")

    try:
        all_paths = list(folder_path.rglob("*"))
    except OSError as error:
        raise ManufacturingValidationError(f"Unreadable folder '{folder_path}': {error}") from error

    supported = [path for path in all_paths if _is_batch_supported_file(path)]
    supported.sort(key=lambda path: path.relative_to(folder_path).as_posix().lower())
    return tuple(supported)


class FolderImportAdapter(ImportAdapter):
    """The one adapter with no extension: detect() is overridden to check
    Path.is_dir() instead of Path.suffix. parse() recursively scans the
    folder and delegates each supported file to UniversalImportAdapter.
    parse() unmodified -- see this module's own "MWO-LTSA-091" header
    section for the full flow/reuse/return-type rationale. Never
    validates (API.import_validator.validate_import_package), never
    detects conflicts (API.conflict_resolution), never executes
    (API.import_execution_engine) -- adaptation only, same as every other
    adapter in this module."""

    @staticmethod
    def supported_extensions() -> tuple[str, ...]:
        return ()

    @classmethod
    def detect(cls, file_path: Path) -> bool:
        return Path(file_path).is_dir()

    def parse(self, file_path: Path) -> tuple[ImportPackage, ...]:
        file_paths = _scan_folder(Path(file_path))
        return tuple(UniversalImportAdapter.parse(path) for path in file_paths)


# --- Factory -------------------------------------------------------------------

# FolderImportAdapter first: a directory can carry a dotted name (e.g. a
# folder literally named "archive.zip"), and must never be misrouted to an
# extension-based adapter because of it.
_ADAPTERS: tuple[type[ImportAdapter], ...] = (
    FolderImportAdapter,
    JsonImportAdapter,
    PdfImportAdapter,
    ExcelImportAdapter,
    ZipImportAdapter,
)


class UniversalImportAdapter:
    """Factory only: file_path -> detect adapter -> delegate -> ImportPackage.
    No validation. No conflict. No execution. Only adaptation."""

    @staticmethod
    def detect_adapter(file_path: Path) -> type[ImportAdapter]:
        path = Path(file_path)
        for adapter in _ADAPTERS:
            if adapter.detect(path):
                return adapter
        raise ManufacturingValidationError(
            f"Unsupported import source: no adapter detects '{path}' "
            f"(extension '{path.suffix}'). Supported: .json, .pdf, .xlsx, "
            f".xls, .zip, or a directory."
        )

    @classmethod
    def parse(cls, file_path: Path) -> ImportPackage:
        adapter_cls = cls.detect_adapter(file_path)
        return adapter_cls().parse(Path(file_path))


def parse_import_file(file_path: str | Path) -> ImportPackage:
    """The public API this mission requests: file_path -> ImportPackage.
    Detects the right adapter by extension (or directory), delegates to it,
    and returns exactly one canonical ImportPackage -- nothing else.
    Adaptation only: no validation (chain
    API.import_validator.validate_import_package() over this function's
    own result yourself, exactly as pdf_import_parser.py's own docstring
    already requires callers to do), no conflict check, no execution."""
    return UniversalImportAdapter.parse(Path(file_path))


__all__ = [
    "ImportAdapter",
    "JsonImportAdapter",
    "PdfImportAdapter",
    "ExcelImportAdapter",
    "ZipImportAdapter",
    "FolderImportAdapter",
    "UniversalImportAdapter",
    "parse_import_file",
    "PUMP_CANONICAL_FIELDS",
    "SEAL_CANONICAL_FIELDS",
]
