"""LTSA_PDF_CM_PARSER_GENERALIZATION_R1 -- canonical, read-only parser for
the "CONDITION MONITORING ACTUAL MEASURING REPORT" table inside historical
monthly "Laporan PM, CM & Pemasangan Seal" PDFs (John Crane / PT Tommy
Adji Prasetyo / Pertamina RU II Dumai).

Supersedes historical_pm_cmon_extraction.extract_cm_measuring_candidates()
(kept, marked deprecated, never deleted by this MWO) as the ONE canonical
PDF CM extraction path. That legacy function needs a caller-supplied page
range and trusts fixed extract_tables() column indexes; this module needs
neither:

  PDF
  -> CM section detection   (page text markers, never page numbers)
  -> page-local geometry    (column identity from THIS page's own header
                             words; cell bounds from THIS page's own drawn
                             table rectangles -- never fixed x coordinates)
  -> raw row extraction     (RAW SOURCE LAYER -- literal strings, source
                             labels, page/row provenance, never discarded)
  -> canonical normalization (condition_monitoring_reading field names)
  -> validation result      (row continuity, duplicates, dates, tags,
                             header-structure fingerprint)

Proven against the OM & UTL October 2025 reference report (123/123 rows,
0 rejected, 11/11 visual spot checks) and reproduced by
TEST/test_historical_cm_pdf_parser.py.

Locked semantics (Chief Architect directive, never relaxed here):
  * blank cell -> None. Never forward-filled, never copied from a previous
    row, never DE->NDE, never inferred, never derived from master data.
  * Mechanical Seal Leak: Y -> True, N -> False, blank -> None.
  * source API PLAN -> api_plan_snapshot only; ltsa_pumps.api_plan is never
    read or written by this module.
  * one physical table row == one source occurrence. Rows are never
    merged or collapsed, even for a repeated tag/date.
  * the source artifact is never "corrected": misspelled source labels
    ("Quinch", "Flushing Cut (LBO)") are preserved verbatim next to their
    canonical mapping.

This module NEVER writes to a database, NEVER OCRs, and NEVER modifies the
source file. Asset matching and production-duplicate classification are
out of scope (a separate, governed reconciliation gate).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from collections import Counter
from typing import Any, Iterable, Literal

import pdfplumber

from historical_pm_cmon_extraction import _parse_leak_cell, _parse_numeric_cell, sha256_file

PARSER_NAME = "ltsa_historical_cm_pdf_parser"
PARSER_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Terminology: source DE/NDE group -> canonical column stem. Identified from
# the header words physically ABOVE each DE/NDE pair on the page itself (so
# a reordered or renamed group is detected, never silently mis-mapped).
# Order matters: more specific keyword sets first.
# ---------------------------------------------------------------------------

_PAIR_GROUP_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("mechanical_seal_leak", ("LEAK",)),
    ("flushing_in_temp", ("LBI",)),
    ("flushing_out_temp", ("LBO",)),
    ("cooling_water_in_temp", ("COOLING", "IN")),
    ("cooling_water_out_temp", ("COOLING", "OUT")),
    ("mechseal_temp", ("MECHSEAL",)),
    ("water_jacket_temp", ("JACKET",)),
    ("quench_temp", ("QUINCH",)),
    ("quench_temp", ("QUENCH",)),
    ("flushing_temp", ("FLUSHING",)),
)

# FORMAT_A's exact DE/NDE group order (the reference report and every
# layout observed in the 2025/2026 archive). A page whose detected order
# differs is still parsed by label, but reported as a structure change.
FORMAT_A_PAIR_ORDER: tuple[str, ...] = (
    "flushing_temp",
    "quench_temp",
    "flushing_in_temp",
    "flushing_out_temp",
    "cooling_water_in_temp",
    "cooling_water_out_temp",
    "mechseal_temp",
    "mechanical_seal_leak",
    "water_jacket_temp",
)

# Identity columns (raw layer only). Suction/Discharge headers are matched
# by prefix because the source wraps them across two lines ("Sucti|on",
# "Disch|arge").
_IDENTITY_KEYS = ("source_row_number", "raw_date", "raw_tag", "raw_api_plan")

_LEAK_COLUMNS = frozenset({"mechanical_seal_leak_de", "mechanical_seal_leak_nde"})
_TEXT_COLUMNS = frozenset({"pump_operating_state"})
_NUMERIC_TEXT = re.compile(r"^-?\d+([.,]\d+)?$")
_DATE_FORMATS = ("%d-%b-%y", "%d-%b-%Y", "%d/%m/%Y", "%d/%m/%y")

# Fragmented-header letter sets (see _pair_label / API PLAN detection).
_FRAGMENTED_PAIR_LABELS: tuple[tuple[str, str], ...] = (("mechanical_seal_leak", "MECHANICALSEALLEAKYN"),)
_API_PLAN_LETTERS = Counter("APIPLAN")

FormatClass = Literal[
    "FORMAT_A_COMPATIBLE", "CONFIGURABLE_VARIANT", "NEW_ADAPTER_REQUIRED", "UNSUPPORTED", "NO_CM_DATA"
]
_DATE_LIKE = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$")


class LayoutError(ValueError):
    """The page is a CM page but its header geometry cannot be trusted."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CMColumn:
    raw_key: str  # canonical target key, or identity key (raw_date, ...)
    source_label: str  # header words as printed, e.g. "Quinch (°C) / DE"
    x_left: float
    x_right: float


@dataclass(frozen=True, slots=True)
class CMPageLayout:
    page_number: int
    columns: tuple[CMColumn, ...]
    header_bottom: float
    boundary_method: Literal["TABLE_RECTS", "HEADER_MIDPOINTS"]
    fingerprint: str  # ordered raw keys -- equal fingerprints == same structure
    variant_notes: tuple[str, ...] = ()


@dataclass(slots=True)
class CMRawRow:
    """RAW SOURCE LAYER: literal source strings plus provenance."""

    source_document: str
    source_hash: str
    source_page: int
    source_report_page: int | None
    line_top: float
    source_row_number: str | None
    raw_date: str | None
    raw_tag: str | None
    raw_api_plan: str | None
    raw_values: dict[str, str | None]  # canonical key -> literal cell text
    source_labels: dict[str, str]  # canonical key -> source header label
    issues: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CMOccurrence:
    """CANONICAL LAYER: condition_monitoring_reading-compatible fields."""

    source_document: str
    source_hash: str
    source_page: int
    source_report_page: int | None
    source_row_number: int
    source_date: str
    source_tag: str
    asset_code: str
    reading_date: str  # ISO yyyy-mm-dd
    api_plan_snapshot: str | None
    measurements: dict[str, float | bool | str | None]
    # Parsed faithfully but held back from any import by a document-level
    # rule (e.g. a date outside the report's own period). Never "fixed".
    quarantine_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CMRejectedRow:
    raw: CMRawRow
    reasons: list[str]


@dataclass(slots=True)
class CMDocumentResult:
    source_path: str
    source_document: str
    source_hash: str
    page_count: int
    text_layer_chars: int
    cm_pages: list[int]
    layouts: list[CMPageLayout]
    layout_errors: list[dict[str, Any]]
    raw_rows: list[CMRawRow]
    occurrences: list[CMOccurrence]
    rejected: list[CMRejectedRow]
    non_data_lines: list[dict[str, Any]]
    empty_cm_pages: list[dict[str, Any]]
    structure_errors: list[dict[str, Any]]
    validation: dict[str, Any]
    format_class: FormatClass


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------


def is_cm_page_text(text: str) -> bool:
    """A CM table page: the "Actual Measuring Report" title plus the table's
    own identity/measurement headers. Text-only -- no page numbers."""
    upper = (text or "").upper()
    return (
        "ACTUAL MEASURING REPORT" in upper
        and "TAG" in upper
        and "MECHSEAL" in upper
        and "DE NDE" in upper
    )


# ---------------------------------------------------------------------------
# Page-local geometry
# ---------------------------------------------------------------------------


def _center(word: dict[str, Any]) -> float:
    return (word["x0"] + word["x1"]) / 2


def _group_lines(words: Iterable[dict[str, Any]], tolerance: float = 2.5) -> list[list[dict[str, Any]]]:
    """Groups words into physical lines by `top` within `tolerance` points
    (source headers are not always on one exact baseline -- the HSC layout's
    DE/NDE row varies by 0.5pt)."""
    lines: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0]["top"] - word["top"]) <= tolerance:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def _vertical_boundaries(rects: Iterable[dict[str, Any]], y_min: float, y_max: float) -> list[float]:
    """Clustered x positions of the drawn table's vertical cell borders
    that overlap the header band [y_min, y_max]."""
    edges: list[float] = []
    for rect in rects:
        if rect["bottom"] < y_min or rect["top"] > y_max:
            continue
        width = rect["x1"] - rect["x0"]
        height = rect["bottom"] - rect["top"]
        if width <= 3 and height > 3:  # a drawn vertical rule
            edges.append((rect["x0"] + rect["x1"]) / 2)
        elif height > 3:
            edges.extend((rect["x0"], rect["x1"]))
    clusters: list[list[float]] = []
    for edge in sorted(edges):
        if clusters and edge - clusters[-1][-1] <= 4:
            clusters[-1].append(edge)
        else:
            clusters.append([edge])
    return [sum(c) / len(c) for c in clusters]


def _letters(words: Iterable[dict[str, Any]]) -> Counter[str]:
    return Counter(ch for w in words for ch in w["text"].upper() if ch.isalpha())


def _pair_label(words: list[dict[str, Any]]) -> tuple[str | None, str]:
    upper_tokens = {w["text"].upper().strip("()") for w in words}
    joined = " ".join(w["text"] for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])))
    for stem, keywords in _PAIR_GROUP_RULES:
        if all(any(k == t or (len(k) > 3 and k in t) for t in upper_tokens) for k in keywords):
            return stem, joined
    # Squeezed multi-line header text extracts as interleaved fragments
    # ("M S e e c a h l a L n e i a c k a l"). Accepted only when the
    # letters are EXACTLY one known label's letters (anagram), never a
    # partial/fuzzy match.
    letters = _letters(words)
    for stem, label_text in _FRAGMENTED_PAIR_LABELS:
        if letters == Counter(label_text):
            return stem, joined
    return None, joined


def detect_page_layout(
    words: list[dict[str, Any]], rects: list[dict[str, Any]], page_number: int
) -> CMPageLayout:
    """Derives this page's column identities and cell bounds from its own
    header. Raises LayoutError when anything is ambiguous -- never guesses."""
    lines = _group_lines(words)
    de_line = next(
        (ln for ln in lines if sum(w["text"] == "DE" for w in ln) >= 9 and sum(w["text"] == "NDE" for w in ln) >= 9),
        None,
    )
    if de_line is None:
        raise LayoutError("DE/NDE header row not found")
    tokens = [w for w in de_line if w["text"] in ("DE", "NDE")]
    if [w["text"] for w in tokens] != ["DE", "NDE"] * (len(tokens) // 2) or len(tokens) % 2:
        raise LayoutError(f"DE/NDE header row is not strictly alternating: {[w['text'] for w in tokens]}")
    header_bottom = max(w["bottom"] for w in de_line)
    de_top = min(w["top"] for w in de_line)

    anchors = [w for w in words if w["top"] < de_top and w["text"].upper() in ("API", "NO", "DATE", "TAG")]
    if not anchors:
        raise LayoutError("identity header (No/Date/Tag/API) not found")
    # The header band starts just below the group caption row ("1 2 Cooler
    # / Reservoir / Thermosyphon 4 5 ...") when present -- squeezed two-line
    # labels ("API / PLAN") can sit a few points above the "Tag" baseline.
    caption_lines = [
        ln for ln in lines if ln[0]["top"] < de_top and any(w["text"].upper() == "THERMOSYPHON" for w in ln)
    ]
    if caption_lines:
        header_top = caption_lines[-1][0]["top"] + 2.5
    else:
        header_top = min(w["top"] for w in anchors) - 2
    header_words = [w for w in words if header_top <= w["top"] < de_top - 0.5]

    def find_header(predicate) -> dict[str, Any]:
        found = [w for w in header_words if predicate(w["text"])]
        if len(found) != 1:
            raise LayoutError(f"expected exactly one header word, found {[w['text'] for w in found]}")
        return found[0]

    no_w = find_header(lambda t: t.upper() == "NO")
    date_w = find_header(lambda t: t.upper() == "DATE")
    tag_w = find_header(lambda t: t.upper() == "TAG")
    # API PLAN: every header word between the Tag header and the first DE
    # column must spell exactly "API PLAN" -- as two words, or as the
    # interleaved fragments ("P A LA PI N") of the squeezed HSC header.
    plan_words = [w for w in header_words if tag_w["x1"] + 1 < _center(w) < tokens[0]["x0"] - 1]
    plan_words = [w for w in plan_words if w["text"].upper() not in ("NUMBER",)]
    if not plan_words or _letters(plan_words) != _API_PLAN_LETTERS:
        raise LayoutError(f"API PLAN header not found (saw {[w['text'] for w in plan_words]})")
    plan_x = sum(_center(w) for w in plan_words) / len(plan_words)
    suction_w = find_header(lambda t: t.upper().startswith("SUCTI"))
    discharge_w = find_header(lambda t: t.upper().startswith("DISCH"))
    status_found = [w for w in header_words if w["text"].upper() == "STATUS" and w["x0"] > discharge_w["x0"]]
    if len(status_found) > 1:
        raise LayoutError("multiple Status headers")

    # (raw_key, x_center, source_label)
    anchors_x: list[tuple[str, float, str]] = [
        ("source_row_number", _center(no_w), "No"),
        ("raw_date", _center(date_w), "Date"),
        ("raw_tag", _center(tag_w), "Tag Number"),
        ("raw_api_plan", plan_x, "API PLAN"),
    ]
    pair_order: list[str] = []
    for i in range(0, len(tokens), 2):
        de_w, nde_w = tokens[i], tokens[i + 1]
        lo, hi = de_w["x0"] - 6, nde_w["x1"] + 6
        above = [w for w in header_words if lo <= _center(w) <= hi and w not in plan_words]
        stem, label = _pair_label(above)
        if stem is None:
            raise LayoutError(f"unrecognised DE/NDE group header {label!r}")
        if stem in pair_order:
            raise LayoutError(f"duplicate DE/NDE group {stem!r} ({label!r})")
        pair_order.append(stem)
        anchors_x.append((f"{stem}_de", _center(de_w), f"{label} / DE"))
        anchors_x.append((f"{stem}_nde", _center(nde_w), f"{label} / NDE"))
    suction_label = " ".join(w["text"] for w in header_words if abs(_center(w) - _center(suction_w)) < 12)
    anchors_x.append(("suction_temp", _center(suction_w), suction_label or "Suction"))
    discharge_label = " ".join(w["text"] for w in header_words if abs(_center(w) - _center(discharge_w)) < 12)
    anchors_x.append(("discharge_temp", _center(discharge_w), discharge_label or "Discharge"))
    if status_found:
        anchors_x.append(("pump_operating_state", _center(status_found[0]), "Status"))

    xs = [x for _, x, _ in anchors_x]
    if xs != sorted(xs):
        raise LayoutError("header columns are not in left-to-right order")

    # Cell bounds: prefer the page's own drawn table rules; every column
    # anchor must fall in its own distinct cell, else fall back to header
    # midpoints (recorded in boundary_method).
    boundaries = _vertical_boundaries(rects, de_top, header_bottom)
    method: Literal["TABLE_RECTS", "HEADER_MIDPOINTS"] = "TABLE_RECTS"
    cells: list[tuple[float, float]] = []
    if len(boundaries) >= len(anchors_x) + 1:
        for _, x, _ in anchors_x:
            left = max((b for b in boundaries if b < x), default=None)
            right = min((b for b in boundaries if b > x), default=None)
            if left is None or right is None:
                cells = []
                break
            cells.append((left, right))
        if len(set(cells)) != len(anchors_x):
            cells = []
    if not cells:
        method = "HEADER_MIDPOINTS"
        mids = [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)]
        first_w = xs[1] - xs[0]
        last_w = xs[-1] - xs[-2]
        edges = [xs[0] - first_w / 2, *mids, xs[-1] + last_w / 2]
        cells = [(edges[i], edges[i + 1]) for i in range(len(xs))]

    columns = tuple(
        CMColumn(raw_key=key, source_label=label, x_left=cell[0], x_right=cell[1])
        for (key, _, label), cell in zip(anchors_x, cells)
    )
    fragmented = any(len(w["text"]) <= 2 for w in plan_words)
    return CMPageLayout(
        page_number=page_number,
        columns=columns,
        header_bottom=header_bottom,
        boundary_method=method,
        fingerprint="|".join(c.raw_key for c in columns),
        variant_notes=("FRAGMENTED_HEADER_LABELS",) if fragmented else (),
    )


def classify_layout(layout: CMPageLayout) -> FormatClass:
    pair_stems = [c.raw_key[: -len("_de")] for c in layout.columns if c.raw_key.endswith("_de")]
    keys = [c.raw_key for c in layout.columns]
    base = list(_IDENTITY_KEYS) + [f"{s}_{side}" for s in FORMAT_A_PAIR_ORDER for side in ("de", "nde")]
    if keys == base + ["suction_temp", "discharge_temp"] and not layout.variant_notes:
        return "FORMAT_A_COMPATIBLE"
    if keys == base + ["suction_temp", "discharge_temp"]:
        return "CONFIGURABLE_VARIANT"  # FORMAT_A columns, fragmented header text
    if keys == base + ["suction_temp", "discharge_temp", "pump_operating_state"]:
        return "CONFIGURABLE_VARIANT"  # FORMAT_A + trailing Status column
    if sorted(pair_stems) == sorted(FORMAT_A_PAIR_ORDER):
        return "CONFIGURABLE_VARIANT"  # same fields, different order
    return "NEW_ADAPTER_REQUIRED"


# ---------------------------------------------------------------------------
# Raw extraction
# ---------------------------------------------------------------------------

_REPORT_PAGE_RE = re.compile(r"Page\s+(\d+)\s*$")


def detect_body_subdivisions(
    rects: list[dict[str, Any]], layout: CMPageLayout, body_top: float, body_bottom: float
) -> list[str]:
    """Columns whose BODY cells are split by drawn rules the header does not
    define (the HSC & SPK Jan-Apr 2026 layout draws 4 sub-cells under each
    LBI/LBO/Cooling Water DE/NDE pair). The header gives those sub-cells no
    meaning, so mapping them would be a guess -- the page needs a new
    adapter instead."""
    body_edges = _vertical_boundaries(rects, body_top, body_bottom)
    return [c.raw_key for c in layout.columns if any(c.x_left + 3 < b < c.x_right - 3 for b in body_edges)]


def extract_raw_rows(
    words: list[dict[str, Any]],
    layout: CMPageLayout,
    *,
    source_document: str,
    source_hash: str,
    page_text: str = "",
) -> tuple[list[CMRawRow], list[dict[str, Any]]]:
    """(raw rows, non-data lines) for the table body below the header.

    A line carrying a row number, date or tag is a source row (kept even if
    malformed, with issues). A line carrying none of them -- e.g. a large
    "TA" (turnaround) marker across an empty table -- is returned as a
    non-data line, preserved verbatim, never counted as a row."""
    report_page_match = _REPORT_PAGE_RE.search(page_text.strip()) if page_text else None
    report_page = int(report_page_match.group(1)) if report_page_match else None
    footer_top = min((w["top"] for w in words if w["text"] == "Page" and w["top"] > layout.header_bottom), default=None)
    table_left = layout.columns[0].x_left - 2
    table_right = layout.columns[-1].x_right + 2

    body = [
        w
        for w in words
        if w["top"] > layout.header_bottom + 1
        and (footer_top is None or w["top"] < footer_top - 1)
        and table_left <= _center(w) <= table_right
    ]
    labels = {c.raw_key: c.source_label for c in layout.columns}
    rows: list[CMRawRow] = []
    non_data: list[dict[str, Any]] = []
    for line in _group_lines(body):
        cells: dict[str, list[str]] = {}
        issues: list[str] = []
        for word in line:
            x = _center(word)
            column = next((c for c in layout.columns if c.x_left <= x < c.x_right), None)
            if column is None:
                issues.append(f"token {word['text']!r} at x={x:.1f} is outside every column")
                continue
            cells.setdefault(column.raw_key, []).append(word["text"])
        values = {key: " ".join(parts) for key, parts in cells.items()}
        if not any(values.get(k) for k in ("source_row_number", "raw_date", "raw_tag")):
            non_data.append(
                {
                    "source_page": layout.page_number,
                    "line_top": round(line[0]["top"], 2),
                    "text": " ".join(w["text"] for w in line),
                }
            )
            continue
        for key, parts in cells.items():
            if len(parts) > 1 and key not in ("raw_tag", "raw_date", "pump_operating_state"):
                issues.append(f"column {key} holds several tokens {parts!r}")
        row_number = values.get("source_row_number")
        if row_number is None or not row_number.isdigit():
            issues.append("no leading row number")
        rows.append(
            CMRawRow(
                source_document=source_document,
                source_hash=source_hash,
                source_page=layout.page_number,
                source_report_page=report_page,
                line_top=round(line[0]["top"], 2),
                source_row_number=row_number,
                raw_date=values.get("raw_date"),
                raw_tag=values.get("raw_tag"),
                raw_api_plan=values.get("raw_api_plan"),
                raw_values={
                    c.raw_key: values.get(c.raw_key) for c in layout.columns if c.raw_key not in _IDENTITY_KEYS
                },
                source_labels=labels,
                issues=issues,
            )
        )
    return rows, non_data


# ---------------------------------------------------------------------------
# Canonical normalization
# ---------------------------------------------------------------------------


def parse_source_date(raw: str | None) -> date | None:
    text = (raw or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_tag(raw: str | None) -> str | None:
    """Typography only: uppercases and removes whitespace (the HSC layout
    prints '200 - P - 1A'). Never touches a letter, digit or separator --
    asset identity resolution is the reconciliation gate's job."""
    if raw is None:
        return None
    collapsed = re.sub(r"\s+", "", raw).upper()
    return collapsed or None


def normalize_row(raw: CMRawRow) -> CMOccurrence | CMRejectedRow:
    reasons = list(raw.issues)
    reading_date = parse_source_date(raw.raw_date)
    if raw.raw_date is None:
        reasons.append("missing date")
    elif reading_date is None:
        reasons.append(f"unparseable date {raw.raw_date!r}")
    asset_code = normalize_tag(raw.raw_tag)
    if asset_code is None:
        reasons.append("missing tag")

    measurements: dict[str, float | bool | str | None] = {}
    for key, value in raw.raw_values.items():
        text = None if value is None else value.strip() or None
        if key in _LEAK_COLUMNS:
            if text is not None and text.upper() not in ("Y", "N"):
                reasons.append(f"{key}: invalid leak value {text!r}")
            measurements[key] = _parse_leak_cell(text)
        elif key in _TEXT_COLUMNS:
            measurements[key] = text
        else:
            if text is not None and not _NUMERIC_TEXT.match(text):
                reasons.append(f"{key}: non-numeric value {text!r}")
            measurements[key] = _parse_numeric_cell(text)

    if reasons:
        return CMRejectedRow(raw=raw, reasons=reasons)
    assert reading_date is not None and asset_code is not None and raw.source_row_number is not None
    return CMOccurrence(
        source_document=raw.source_document,
        source_hash=raw.source_hash,
        source_page=raw.source_page,
        source_report_page=raw.source_report_page,
        source_row_number=int(raw.source_row_number),
        source_date=raw.raw_date or "",
        source_tag=raw.raw_tag or "",
        asset_code=asset_code,
        reading_date=reading_date.isoformat(),
        api_plan_snapshot=(raw.raw_api_plan or "").strip() or None,
        measurements=measurements,
    )


def apply_report_period(occurrences: list[CMOccurrence], report_period: tuple[int, int] | None) -> None:
    """Quarantines (never edits) occurrences dated outside the report's own
    (year, month) -- e.g. '06-Jan-25' rows inside a January 2026 report."""
    if report_period is None:
        return
    year, month = report_period
    for occurrence in occurrences:
        reading = date.fromisoformat(occurrence.reading_date)
        if (reading.year, reading.month) != (year, month):
            occurrence.quarantine_reasons.append(
                f"date {occurrence.source_date!r} outside report period {year:04d}-{month:02d}"
            )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_rows(
    raw_rows: list[CMRawRow], occurrences: list[CMOccurrence], rejected: list[CMRejectedRow], layouts: list[CMPageLayout]
) -> dict[str, Any]:
    numbered = [int(r.source_row_number) for r in raw_rows if r.source_row_number and r.source_row_number.isdigit()]
    counts: dict[int, int] = {}
    for n in numbered:
        counts[n] = counts.get(n, 0) + 1
    lo, hi = (min(numbered), max(numbered)) if numbered else (None, None)
    missing = [n for n in range(lo, hi + 1) if n not in counts] if lo is not None else []
    order_breaks = [
        (numbered[i - 1], numbered[i]) for i in range(1, len(numbered)) if numbered[i] <= numbered[i - 1]
    ]
    dates = sorted(o.reading_date for o in occurrences)
    fingerprints = sorted({layout.fingerprint for layout in layouts})
    return {
        "source_row_min": lo,
        "source_row_max": hi,
        "missing_source_row_numbers": missing,
        "duplicate_source_row_numbers": sorted(n for n, c in counts.items() if c > 1),
        "row_order_breaks": order_breaks,
        "rows_without_row_number": sum(1 for r in raw_rows if not (r.source_row_number or "").isdigit()),
        "rows_without_date": sum(1 for r in raw_rows if r.raw_date is None),
        "rows_without_tag": sum(1 for r in raw_rows if r.raw_tag is None),
        "unparseable_dates": sorted(
            {r.raw_date for r in raw_rows if r.raw_date is not None and parse_source_date(r.raw_date) is None}
        ),
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "distinct_tags": len({o.asset_code for o in occurrences}),
        "quarantined_rows": sum(1 for o in occurrences if o.quarantine_reasons),
        "header_fingerprints": fingerprints,
        "header_structure_changes": len(fingerprints) > 1,
        "boundary_methods": sorted({layout.boundary_method for layout in layouts}),
        "variant_notes": sorted({n for layout in layouts for n in layout.variant_notes}),
        "rejected_reasons": [
            {"source_page": r.raw.source_page, "source_row_number": r.raw.source_row_number, "reasons": r.reasons}
            for r in rejected
        ],
    }


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def parse_cm_pdf(path: str | Path, *, report_period: tuple[int, int] | None = None) -> CMDocumentResult:
    """Parses every CM Actual Measuring Report page of one PDF. Read-only.
    `report_period` = the report's own (year, month) when the caller knows
    it; rows dated outside it are quarantined, never corrected."""
    path = Path(path)
    source_hash = sha256_file(path)
    cm_pages: list[int] = []
    layouts: list[CMPageLayout] = []
    layout_errors: list[dict[str, Any]] = []
    structure_errors: list[dict[str, Any]] = []
    empty_pages: list[dict[str, Any]] = []
    non_data_lines: list[dict[str, Any]] = []
    raw_rows: list[CMRawRow] = []
    text_chars = 0
    with pdfplumber.open(str(path)) as pdf:
        page_count = len(pdf.pages)
        for page_number, page in enumerate(pdf.pages, start=1):
            text_chars += len(page.chars)
            text = page.extract_text() or ""
            if not is_cm_page_text(text):
                continue
            cm_pages.append(page_number)
            words = page.extract_words()
            try:
                layout = detect_page_layout(words, page.rects, page_number)
            except LayoutError as exc:
                if not any(_DATE_LIKE.match(w["text"]) for w in words):
                    empty_pages.append({"page": page_number, "reason": f"no data rows; {exc}"})
                else:
                    layout_errors.append({"page": page_number, "error": str(exc)})
                continue
            page_rows, page_non_data = extract_raw_rows(
                words, layout, source_document=path.name, source_hash=source_hash, page_text=text
            )
            non_data_lines.extend(page_non_data)
            if not page_rows:
                empty_pages.append(
                    {"page": page_number, "reason": "no data rows", "markers": [n["text"] for n in page_non_data]}
                )
            subdivided = detect_body_subdivisions(page.rects, layout, layout.header_bottom + 2, page.height - 40)
            if subdivided and page_rows:
                structure_errors.append({"page": page_number, "unlabelled_body_subcolumns": subdivided})
                for raw in page_rows:
                    raw.issues.append(f"page body subdivides header columns {subdivided} -- NEW_ADAPTER_REQUIRED")
            layouts.append(layout)
            raw_rows.extend(page_rows)

    occurrences: list[CMOccurrence] = []
    rejected: list[CMRejectedRow] = []
    for raw in raw_rows:
        result = normalize_row(raw)
        (occurrences if isinstance(result, CMOccurrence) else rejected).append(result)
    apply_report_period(occurrences, report_period)

    pages_with_rows = {r.source_page for r in raw_rows}
    classes = {classify_layout(layout) for layout in layouts if layout.page_number in pages_with_rows}
    if not raw_rows and not layout_errors and empty_pages:
        format_class: FormatClass = "NO_CM_DATA"
    elif not layouts:
        format_class = "UNSUPPORTED"
    elif layout_errors or structure_errors or "NEW_ADAPTER_REQUIRED" in classes:
        format_class = "NEW_ADAPTER_REQUIRED"
    elif "CONFIGURABLE_VARIANT" in classes:
        format_class = "CONFIGURABLE_VARIANT"
    else:
        format_class = "FORMAT_A_COMPATIBLE"

    validation = validate_rows(raw_rows, occurrences, rejected, layouts)
    validation["layout_errors"] = layout_errors
    validation["structure_errors"] = structure_errors
    validation["empty_cm_pages"] = empty_pages
    validation["non_data_lines"] = len(non_data_lines)
    return CMDocumentResult(
        source_path=str(path),
        source_document=path.name,
        source_hash=source_hash,
        page_count=page_count,
        text_layer_chars=text_chars,
        cm_pages=cm_pages,
        layouts=layouts,
        layout_errors=layout_errors,
        raw_rows=raw_rows,
        occurrences=occurrences,
        rejected=rejected,
        non_data_lines=non_data_lines,
        empty_cm_pages=empty_pages,
        structure_errors=structure_errors,
        validation=validation,
        format_class=format_class,
    )


__all__ = [
    "PARSER_NAME",
    "PARSER_VERSION",
    "FORMAT_A_PAIR_ORDER",
    "CMColumn",
    "CMPageLayout",
    "CMRawRow",
    "CMOccurrence",
    "CMRejectedRow",
    "CMDocumentResult",
    "LayoutError",
    "is_cm_page_text",
    "detect_page_layout",
    "classify_layout",
    "detect_body_subdivisions",
    "extract_raw_rows",
    "parse_source_date",
    "normalize_tag",
    "normalize_row",
    "apply_report_period",
    "validate_rows",
    "parse_cm_pdf",
]
