"""LTSA_PDF_CM_PARSER_GENERALIZATION_R1 -- READ-ONLY archive dry run for
historical_cm_pdf_parser.py.

Walks a PM/CM history archive (e.g. D:\\PROJECT\\Source-documents\\LTSA\\
PM_CM_HISTORY\\<year>\\...), parses every PDF's CM Actual Measuring Report
with the canonical parser, and writes SOURCE-coverage artifacts only:

  <out>/ltsa_pdf_cm_archive_manifest.json    one record per PDF
  <out>/ltsa_pdf_cm_archive_manifest.csv     same, flat
  <out>/ltsa_pdf_cm_archive_validation.json  aggregate + per-document checks
  <out>/ltsa_pdf_cm_archive_occurrences.jsonl  canonical occurrences (with
                                              import_eligible / quarantine)
  <out>/ltsa_pdf_cm_archive_raw_rows.jsonl    raw source layer, every row

Never writes to a database, never OCRs, never copies or modifies a source
PDF. "Eligible" means only "structurally trustworthy source row" -- asset
matching and production duplicate classification belong to the separate
reconciliation gate and are reported as DEFERRED here.

Usage:
  python historical_cm_pdf_archive_dry_run.py --root <archive> --years 2025 2026 --out <dir>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from historical_cm_pdf_parser import PARSER_NAME, PARSER_VERSION, CMDocumentResult, parse_cm_pdf

# Month tokens as they appear in the archive's own file names (English and
# Indonesian, including the source's own "FEBUARI" spelling).
_MONTH_TOKENS: dict[str, int] = {
    "JANUARY": 1, "JANUARI": 1, "JAN": 1,
    "FEBRUARY": 2, "FEBRUARI": 2, "FEBUARI": 2, "FEB": 2,
    "MARCH": 3, "MARET": 3, "MAR": 3,
    "APRIL": 4, "APR": 4,
    "MAY": 5, "MEI": 5,
    "JUNE": 6, "JUNI": 6, "JUN": 6,
    "JULY": 7, "JULI": 7, "JUL": 7,
    "AUGUST": 8, "AGUSTUS": 8, "AUG": 8, "AGU": 8,
    "SEPTEMBER": 9, "SEP": 9,
    "OCTOBER": 10, "OKTOBER": 10, "OCT": 10, "OKT": 10,
    "NOVEMBER": 11, "NOV": 11,
    "DECEMBER": 12, "DESEMBER": 12, "DEC": 12, "DES": 12,
}
# Area codes as printed in file names -> one normalized area label. The
# combined contract areas stay combined (OM & UTL, HSC & SPK) -- MA
# resolution is not this tool's job.
_AREA_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bOM\s*(&|AND)?\s*UTL\b", "OM_UTL"),
    (r"\bHSC\s*(&|AND)?\s*SPK\b", "HSC_SPK"),
    (r"\bHCC\b", "HCC"),
    (r"\bHOC\b", "HOC"),
    (r"\bHSC\b", "HSC_SPK"),
    (r"\bOM\b", "OM_UTL"),
)
TEXT_LAYER_MIN_CHARS_PER_PAGE = 50

MANIFEST_FIELDS = (
    "year", "month", "area", "folder_area", "pdf", "relative_path", "sha256", "page_count",
    "discovery_status", "format_class", "cm_pages", "raw_rows", "parsed_rows", "rejected_rows",
    "quarantined_rows", "eligible_rows", "distinct_tags", "date_min", "date_max",
    "source_row_min", "source_row_max", "missing_source_row_numbers", "duplicate_source_row_numbers",
    "metadata_warnings", "failure_reason",
)


def _area_from(text: str) -> str | None:
    upper = text.upper()
    for pattern, area in _AREA_PATTERNS:
        if re.search(pattern, upper):
            return area
    return None


def derive_metadata(path: Path, root: Path) -> dict[str, Any]:
    """Year from the archive's top-level year folder; month and area from
    the file name (the document's own identity), cross-checked against the
    folder names. Mismatches are warnings, never silently resolved."""
    relative = path.relative_to(root)
    warnings: list[str] = []
    year = int(relative.parts[0]) if relative.parts[0].isdigit() else None
    if year is None:
        warnings.append("no year folder")

    name = path.stem.upper()
    subject = name.split("SEAL", 1)[1] if "SEAL" in name else name
    months = {m for token, m in _MONTH_TOKENS.items() if re.search(rf"\b{token}\b", subject)}
    month = months.pop() if len(months) == 1 else None
    if month is None:
        warnings.append(f"month not uniquely derivable from file name ({sorted(months) or 'none'})")

    name_year = re.search(r"\b20(\d{2})\b|'(\d{2})\b|\b(\d{2})$", subject.strip())
    if name_year and year is not None:
        yy = int(next(g for g in name_year.groups() if g))
        if yy != year % 100:
            warnings.append(f"file-name year {yy:02d} differs from year folder {year}")

    area = _area_from(subject)
    folder_parts = [p for p in relative.parts[1:-1]]
    folder_area = next((a for a in (_area_from(p) for p in reversed(folder_parts)) if a), None)
    if area is None:
        warnings.append("area not derivable from file name")
    if area and folder_area and area != folder_area:
        warnings.append(f"file-name area {area} differs from folder area {folder_area}")
    return {"year": year, "month": month, "area": area, "folder_area": folder_area, "metadata_warnings": warnings}


def _document_record(path: Path, root: Path, result: CMDocumentResult | None, error: str | None) -> dict[str, Any]:
    meta = derive_metadata(path, root)
    record: dict[str, Any] = {**meta, "pdf": path.name, "relative_path": str(path.relative_to(root))}
    if result is None:
        record.update({"discovery_status": "PARSER_FAILED", "failure_reason": error, "format_class": None})
        return record
    v = result.validation
    quarantined = sum(1 for o in result.occurrences if o.quarantine_reasons)
    if result.page_count and result.text_layer_chars < TEXT_LAYER_MIN_CHARS_PER_PAGE * result.page_count:
        status = "TEXT_EXTRACTION_UNSUPPORTED"
    elif not result.cm_pages:
        status = "NO_CM_SECTION"
    else:
        status = "CM_SECTION_FOUND"
    failure = None
    if result.layout_errors:
        failure = "; ".join(f"page {e['page']}: {e['error']}" for e in result.layout_errors)
    elif result.structure_errors:
        failure = "; ".join(
            f"page {e['page']}: body sub-columns under {','.join(e['unlabelled_body_subcolumns'])}"
            for e in result.structure_errors
        )
    elif result.format_class == "NO_CM_DATA":
        failure = "CM section present but empty: " + "; ".join(
            f"page {e['page']} {e.get('markers') or e.get('reason')}" for e in result.empty_cm_pages
        )
    record.update(
        {
            "sha256": result.source_hash,
            "page_count": result.page_count,
            "discovery_status": status,
            "format_class": result.format_class if status == "CM_SECTION_FOUND" else None,
            "cm_pages": result.cm_pages,
            "raw_rows": len(result.raw_rows),
            "parsed_rows": len(result.occurrences),
            "rejected_rows": len(result.rejected),
            "quarantined_rows": quarantined,
            "eligible_rows": 0,  # set by the caller once document-level gates are known
            "distinct_tags": v["distinct_tags"],
            "date_min": v["date_min"],
            "date_max": v["date_max"],
            "source_row_min": v["source_row_min"],
            "source_row_max": v["source_row_max"],
            "missing_source_row_numbers": v["missing_source_row_numbers"],
            "duplicate_source_row_numbers": v["duplicate_source_row_numbers"],
            "failure_reason": failure,
        }
    )
    return record


def document_is_eligible(record: dict[str, Any]) -> bool:
    """Document-level gate: only a fully understood layout, with trustworthy
    period metadata and clean row numbering, may contribute eligible rows."""
    return (
        record.get("discovery_status") == "CM_SECTION_FOUND"
        and record.get("format_class") in ("FORMAT_A_COMPATIBLE", "CONFIGURABLE_VARIANT")
        and record.get("year") is not None
        and record.get("month") is not None
        and record.get("area") is not None
        and not record.get("missing_source_row_numbers")
        and not record.get("duplicate_source_row_numbers")
        and not record.get("metadata_warnings")  # any period/area ambiguity quarantines the document
    )


def run(root: Path, years: list[str], out_dir: Path) -> dict[str, Any]:
    pdfs = sorted(p for year in years for p in (root / year).rglob("*") if p.suffix.lower() == ".pdf")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    occurrence_lines: list[str] = []
    raw_lines: list[str] = []
    hash_to_paths: dict[str, list[str]] = defaultdict(list)
    tag_date_docs: dict[tuple[str, str], set[str]] = defaultdict(set)
    parsed_tags: set[str] = set()
    eligible_tags: set[str] = set()

    for path in pdfs:
        meta = derive_metadata(path, root)
        period = (meta["year"], meta["month"]) if meta["year"] and meta["month"] else None
        try:
            result = parse_cm_pdf(path, report_period=period)
            error = None
        except Exception as exc:  # reported per document, never swallowed
            result, error = None, f"{type(exc).__name__}: {exc}"
        record = _document_record(path, root, result, error)
        if result is not None:
            hash_to_paths[result.source_hash].append(record["relative_path"])
            eligible_doc = document_is_eligible(record)
            doc_quarantine = [] if eligible_doc else [f"document not eligible ({record['format_class']}, {record.get('failure_reason') or record['metadata_warnings']})"]
            eligible_rows = 0
            for occ in result.occurrences:
                reasons = list(occ.quarantine_reasons) + doc_quarantine
                eligible = not reasons
                eligible_rows += eligible
                parsed_tags.add(occ.asset_code)
                if eligible:
                    eligible_tags.add(occ.asset_code)
                    tag_date_docs[(occ.asset_code, occ.reading_date)].add(record["relative_path"])
                occurrence_lines.append(
                    json.dumps(
                        {
                            **asdict(occ),
                            "year": record["year"], "month": record["month"], "area": record["area"],
                            "relative_path": record["relative_path"],
                            "import_eligible": eligible,
                            "quarantine_reasons": reasons,
                            "asset_match": "DEFERRED",
                            "production_classification": "DEFERRED",
                        },
                        ensure_ascii=False,
                    )
                )
            for raw in result.raw_rows:
                raw_lines.append(json.dumps({**asdict(raw), "relative_path": record["relative_path"]}, ensure_ascii=False))
            record["eligible_rows"] = eligible_rows
            record["import_eligible_document"] = eligible_doc
            record["validation"] = result.validation
        manifest.append(record)

    duplicate_sources = {h: p for h, p in hash_to_paths.items() if len(p) > 1}
    cross_doc = {f"{k[0]}|{k[1]}": sorted(v) for k, v in tag_date_docs.items() if len(v) > 1}
    aggregate = _aggregate(manifest)
    aggregate["distinct_source_tags_parsed"] = len(parsed_tags)
    aggregate["distinct_source_tags_eligible"] = len(eligible_tags)
    validation = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parser": PARSER_NAME,
        "parser_version": PARSER_VERSION,
        "root": str(root),
        "years": years,
        "mode": "READ_ONLY_DRY_RUN",
        "ocr_used": False,
        "aggregate": aggregate,
        "duplicate_source_files": duplicate_sources,
        "cross_document_same_tag_date": cross_doc,
        "production_classification": {
            k: "DEFERRED"
            for k in (
                "EXACT_PUMP", "EXACT_NON_PUMP", "NOT_FOUND", "AMBIGUOUS",
                "ALREADY_PRESENT", "NEW_CANDIDATE", "POTENTIAL_DUPLICATE", "CONFLICT",
            )
        },
        "documents": [
            {k: r.get(k) for k in ("relative_path", "discovery_status", "format_class", "failure_reason", "metadata_warnings", "validation")}
            for r in manifest
        ],
    }

    (out_dir / "ltsa_pdf_cm_archive_manifest.json").write_text(
        json.dumps({"aggregate": aggregate, "documents": [{k: v for k, v in r.items() if k != "validation"} for r in manifest]}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    with open(out_dir / "ltsa_pdf_cm_archive_manifest.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*MANIFEST_FIELDS, "import_eligible_document"], extrasaction="ignore")
        writer.writeheader()
        for r in manifest:
            writer.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
    (out_dir / "ltsa_pdf_cm_archive_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "ltsa_pdf_cm_archive_occurrences.jsonl").write_text("\n".join(occurrence_lines) + "\n", encoding="utf-8")
    (out_dir / "ltsa_pdf_cm_archive_raw_rows.jsonl").write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    return validation


def _aggregate(manifest: list[dict[str, Any]]) -> dict[str, Any]:
    def total(key: str, rows=None) -> int:
        return sum(r.get(key) or 0 for r in (rows if rows is not None else manifest))

    with_cm = [r for r in manifest if r.get("discovery_status") == "CM_SECTION_FOUND"]
    breakdown: dict[str, dict[str, dict[str, int]]] = {"year": {}, "month": {}, "area": {}}
    for dim in breakdown:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in with_cm:
            key = f"{r['year']}-{r['month']:02d}" if dim == "month" and r.get("month") else str(r.get(dim))
            groups[key].append(r)
        breakdown[dim] = {
            key: {
                "documents": len(rows),
                "raw_rows": total("raw_rows", rows),
                "parsed_rows": total("parsed_rows", rows),
                "rejected_rows": total("rejected_rows", rows),
                "quarantined_rows": total("quarantined_rows", rows),
                "eligible_rows": total("eligible_rows", rows),
            }
            for key, rows in sorted(groups.items())
        }
    return {
        "total_pdfs": len(manifest),
        "pdf_with_cm": len(with_cm),
        "pdf_without_cm": sum(1 for r in manifest if r.get("discovery_status") == "NO_CM_SECTION"),
        "text_extraction_unsupported": sum(1 for r in manifest if r.get("discovery_status") == "TEXT_EXTRACTION_UNSUPPORTED"),
        "parser_failed": sum(1 for r in manifest if r.get("discovery_status") == "PARSER_FAILED"),
        "format_classes": dict(Counter(r.get("format_class") for r in with_cm)),
        "total_cm_source_rows": total("raw_rows"),
        "total_cm_parsed_rows": total("parsed_rows"),
        "total_cm_rejected_rows": total("rejected_rows"),
        "total_cm_quarantined_rows": total("quarantined_rows"),
        "total_cm_eligible_rows": total("eligible_rows"),
        "breakdown": breakdown,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--years", nargs="+", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    validation = run(args.root, args.years, args.out)
    print(json.dumps({k: v for k, v in validation["aggregate"].items() if k != "breakdown"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
