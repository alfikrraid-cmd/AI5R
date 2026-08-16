from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from ltsa_internal_component_ingestion import (
    build_internal_component_projection,
    project_internal_component_rows,
)

_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}

_MECHSEAL_SHEET = "Mechseal"
_GUDANG_SHEET = "Gudang"
_KOSONG_SHEET = "Kosong"


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _normalize_size(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    return text.replace(' "', '"').replace('" ', '"')


def _normalize_seal_name(value: Any) -> str | None:
    text = _clean_text(value)
    if text in {None, "-"}:
        return None
    return text


def _normalize_tag_number(value: Any) -> str | None:
    text = _clean_text(value)
    if text in {None, "-", "N/A"}:
        return None
    return text


def _normalize_gpn(value: Any) -> str | None:
    text = _clean_text(value)
    if text in {None, "-", "N/A"}:
        return None
    return text


def _parse_quantity(value: Any) -> int | None:
    text = _clean_text(value)
    if text is None:
        return None
    match = re.search(r"(\d+)", text)
    if match is None:
        return None
    return int(match.group(1))


def _slug(value: str | None) -> str:
    if value is None:
        return "UNSPEC"
    slug = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")
    return slug or "UNSPEC"


def build_seal_code(seal_name: str | None, shaft_size: str | None) -> str:
    return f"LTSA-SEAL-{_slug(seal_name)}-{_slug(shaft_size)}"


def _sheet_rows(workbook_path: Path, sheet_name: str) -> list[tuple[int, dict[int, str | None]]]:
    with zipfile.ZipFile(workbook_path) as zf:
        shared_strings = _load_shared_strings(zf)
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        relationships = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relationship_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall("pkg:Relationship", _NS)
        }

        sheets = workbook.find("main:sheets", _NS)
        for sheet in list(sheets) if sheets is not None else []:
            if sheet.attrib["name"] != sheet_name:
                continue
            relation_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            target = relationship_map[relation_id]
            sheet_path = (
                f"xl/{target}"
                if target.startswith("worksheets/")
                else f"xl/worksheets/{target.split('/')[-1]}"
            )
            root = ET.fromstring(zf.read(sheet_path))
            rows: list[tuple[int, dict[int, str | None]]] = []
            for row in root.findall(".//main:sheetData/main:row", _NS):
                row_values: dict[int, str | None] = {}
                for cell in row.findall("main:c", _NS):
                    row_values[_column_index(cell.attrib.get("r", ""))] = _read_cell(
                        cell, shared_strings
                    )
                rows.append((int(row.attrib.get("r", "0")), row_values))
            return rows

    raise ValueError(f"Sheet not found: {sheet_name}")


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []

    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    shared_strings: list[str] = []
    for item in root.findall("main:si", _NS):
        shared_strings.append("".join(node.text or "" for node in item.iterfind(".//main:t", _NS)))
    return shared_strings


def _column_index(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + (ord(character.upper()) - 64)
    return index


def _read_cell(cell: ET.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        value = cell.find("main:v", _NS)
        if value is None or value.text is None:
            return None
        return shared_strings[int(value.text)]
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iterfind(".//main:t", _NS))

    value = cell.find("main:v", _NS)
    return value.text if value is not None else None


def project_grouped_inventory_rows(
    rows: list[tuple[int, dict[int, str | None]]]
) -> list[dict[str, Any]]:
    state = {
        "description": None,
        "size": None,
        "area": None,
        "seal_type": None,
        "pump_type": None,
        "contract": None,
        "stock_material": None,
    }
    projected: list[dict[str, Any]] = []

    for row_number, columns in rows:
        if row_number < 11:
            continue

        tag_number = _normalize_tag_number(columns.get(7))
        if tag_number is None:
            continue

        if _clean_text(columns.get(2)) is not None:
            state["description"] = _clean_text(columns.get(2))
        if _normalize_size(columns.get(6)) is not None:
            state["size"] = _normalize_size(columns.get(6))
        if _clean_text(columns.get(11)) is not None:
            state["area"] = _clean_text(columns.get(11))
        if _normalize_seal_name(columns.get(12)) is not None:
            state["seal_type"] = _normalize_seal_name(columns.get(12))
        if _clean_text(columns.get(13)) is not None:
            state["pump_type"] = _clean_text(columns.get(13))
        if _clean_text(columns.get(14)) is not None:
            state["contract"] = _clean_text(columns.get(14))
        if _clean_text(columns.get(15)) is not None:
            state["stock_material"] = _clean_text(columns.get(15))

        projected.append(
            {
                "row_number": row_number,
                "tag_number": tag_number,
                "description": state["description"],
                "shaft_size": state["size"],
                "critical_status": _clean_text(columns.get(8)),
                "series_status": _clean_text(columns.get(9)),
                "drawing_ref": _clean_text(columns.get(10)),
                "area": state["area"],
                "seal_type": state["seal_type"],
                "pump_type": state["pump_type"],
                "contract": state["contract"],
                "stock_material": state["stock_material"],
            }
        )

    return projected


def project_out_of_stock_rows(
    rows: list[tuple[int, dict[int, str | None]]]
) -> list[dict[str, str | None]]:
    projected: list[dict[str, str | None]] = []

    for row_number, columns in rows:
        if row_number < 7:
            continue

        seal_type = _normalize_seal_name(columns.get(3))
        shaft_size = _normalize_size(columns.get(2))
        remarks = _clean_text(columns.get(8))
        ordinal = _clean_text(columns.get(1))

        if seal_type is None and shaft_size is None and remarks is None and ordinal is None:
            continue

        if seal_type is None or shaft_size is None:
            continue

        projected.append(
            {
                "shaft_size": shaft_size,
                "seal_type": seal_type,
                "remarks": remarks,
            }
        )

    return projected


def build_projection(
    mechseal_rows: list[dict[str, Any]],
    gudang_rows: list[dict[str, Any]],
    kosong_rows: list[dict[str, str | None]],
    *,
    known_seals: list[dict[str, Any]] | None = None,
    seal_code_by_identity: dict[tuple[str | None, str | None], str] | None = None,
) -> dict[str, Any]:
    seal_code_by_identity = seal_code_by_identity or _resolve_seal_codes(mechseal_rows, kosong_rows, known_seals or [])

    pumps: dict[str, dict[str, Any]] = {}
    seals: dict[str, dict[str, Any]] = {}
    stock_rows: dict[str, dict[str, Any]] = {}
    compatibility_rows: dict[tuple[str, str], dict[str, Any]] = {}

    for row in mechseal_rows:
        tag_number = row["tag_number"]
        pumps.setdefault(
            tag_number,
            {
                "tag_number": tag_number,
                "area": row.get("area"),
                "pump_type": row.get("pump_type"),
                "seal_type": row.get("seal_type"),
                "drawing_ref": row.get("drawing_ref"),
                "notes": _pump_notes(row),
            },
        )

        identity = (row.get("seal_type"), row.get("shaft_size"))
        seal_code = seal_code_by_identity.get(identity)
        if seal_code is None:
            continue

        seals.setdefault(
            seal_code,
            {
                "seal_code": seal_code,
                "seal_name": row.get("seal_type"),
                "manufacturer": "John Crane",
                "model": row.get("seal_type"),
                "shaft_size": row.get("shaft_size"),
                "status": "ACTIVE",
            },
        )

        compatibility_key = (seal_code, tag_number)
        compatibility_rows.setdefault(
            compatibility_key,
            {
                "seal_code": seal_code,
                "pump_tag_number": tag_number,
                "notes": row.get("contract"),
            },
        )

    for row in gudang_rows:
        identity = (row.get("seal_type"), row.get("shaft_size"))
        seal_code = seal_code_by_identity.get(identity)
        if seal_code is None:
            continue

        seals.setdefault(
            seal_code,
            {
                "seal_code": seal_code,
                "seal_name": row.get("seal_type"),
                "manufacturer": "John Crane",
                "model": row.get("seal_type"),
                "shaft_size": row.get("shaft_size"),
                "status": "ACTIVE",
            },
        )

        quantity = _parse_quantity(row.get("stock_material"))
        if quantity is None:
            continue

        stock = stock_rows.setdefault(
            seal_code,
            {
                "seal_code": seal_code,
                "quantity_on_hand": quantity,
                "reorder_point": 1 if quantity > 0 else 0,
                "location": "Gudang",
                "lifecycle_status": "IN_STOCK" if quantity > 0 else "OUT_OF_STOCK",
                "notes": None,
            },
        )
        if stock["quantity_on_hand"] is None or quantity > stock["quantity_on_hand"]:
            stock["quantity_on_hand"] = quantity
        if quantity > 0:
            stock["lifecycle_status"] = "IN_STOCK"

    for row in kosong_rows:
        identity = (row.get("seal_type"), row.get("shaft_size"))
        seal_code = seal_code_by_identity.get(identity)
        if seal_code is None:
            continue

        seals.setdefault(
            seal_code,
            {
                "seal_code": seal_code,
                "seal_name": row.get("seal_type"),
                "manufacturer": "John Crane",
                "model": row.get("seal_type"),
                "shaft_size": row.get("shaft_size"),
                "status": "ACTIVE",
            },
        )

        stock_rows[seal_code] = {
            "seal_code": seal_code,
            "quantity_on_hand": 0,
            "reorder_point": 1,
            "location": None,
            "lifecycle_status": "OUT_OF_STOCK",
            "notes": row.get("remarks"),
        }

    projection = {
        "metadata": {
            "pump_count": len(pumps),
            "seal_count": len(seals),
            "seal_stock_count": len(stock_rows),
            "compatibility_count": len(compatibility_rows),
            "source_row_count": len(mechseal_rows),
            "source_contracts": Counter(
                row.get("contract") for row in mechseal_rows if row.get("contract")
            ),
        },
        "ltsa_pumps": sorted(pumps.values(), key=lambda row: row["tag_number"]),
        "seal_registry": sorted(seals.values(), key=lambda row: row["seal_code"]),
        "seal_stock": sorted(stock_rows.values(), key=lambda row: row["seal_code"]),
        "seal_pump_compatibility": sorted(
            compatibility_rows.values(),
            key=lambda row: (row["pump_tag_number"], row["seal_code"]),
        ),
    }
    projection["metadata"]["source_contracts"] = dict(
        sorted(projection["metadata"]["source_contracts"].items())
    )
    return projection


def _pump_notes(row: dict[str, Any]) -> str | None:
    parts = []
    if row.get("description"):
        parts.append(f"description={row['description']}")
    if row.get("critical_status"):
        parts.append(f"critical_status={row['critical_status']}")
    if row.get("series_status"):
        parts.append(f"series_status={row['series_status']}")
    if row.get("contract"):
        parts.append(f"contract={row['contract']}")
    return "; ".join(parts) or None


def _resolve_seal_codes(
    mechseal_rows: list[dict[str, Any]],
    kosong_rows: list[dict[str, str | None]],
    known_seals: list[dict[str, Any]],
) -> dict[tuple[str | None, str | None], str]:
    by_exact_identity: dict[tuple[str | None, str | None], str] = {}

    for seal in known_seals:
        seal_name = _normalize_seal_name(seal.get("seal_name"))
        shaft_size = _normalize_size(seal.get("shaft_size"))
        seal_code = _clean_text(seal.get("seal_code"))
        if seal_name is None or seal_code is None:
            continue
        by_exact_identity[(seal_name, shaft_size)] = seal_code

    identities: set[tuple[str | None, str | None]] = set()
    for row in mechseal_rows:
        identities.add((_normalize_seal_name(row.get("seal_type")), _normalize_size(row.get("shaft_size"))))
    for row in kosong_rows:
        identities.add((_normalize_seal_name(row.get("seal_type")), _normalize_size(row.get("shaft_size"))))

    seal_code_by_identity: dict[tuple[str | None, str | None], str] = {}
    for identity in sorted(identities, key=lambda pair: (pair[0] is None, pair[0] or "", pair[1] is None, pair[1] or "")):
        seal_name, shaft_size = identity
        # MWO-LTSA-PUMP-SEAL-DATA-WIRING-001: Seal Type + Seal Size is the
        # frozen V1 compatibility identity -- a row with a type but no
        # parseable size has no safe identity to resolve against (never
        # fabricated as a synthetic "UNSPEC" size bucket, which would
        # silently merge unrelated real sizes together).
        if seal_name is None or shaft_size is None:
            continue
        seal_code_by_identity[identity] = by_exact_identity.get(
            identity, build_seal_code(seal_name, shaft_size)
        )

    return seal_code_by_identity


def ingest_workbook(
    workbook_path: Path,
    *,
    known_seals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    mechseal_rows = project_grouped_inventory_rows(_sheet_rows(workbook_path, _MECHSEAL_SHEET))
    gudang_rows = project_grouped_inventory_rows(_sheet_rows(workbook_path, _GUDANG_SHEET))
    kosong_rows = project_out_of_stock_rows(_sheet_rows(workbook_path, _KOSONG_SHEET))
    seal_code_by_identity = _resolve_seal_codes(mechseal_rows, kosong_rows, known_seals or [])
    projection = build_projection(
        mechseal_rows,
        gudang_rows,
        kosong_rows,
        known_seals=known_seals,
        seal_code_by_identity=seal_code_by_identity,
    )
    projection.update(
        build_internal_component_projection(
            project_internal_component_rows(
                lambda sheet_name: _sheet_rows(workbook_path, sheet_name),
                _clean_text,
                _normalize_size,
                _normalize_gpn,
                _parse_quantity,
                _normalize_seal_name,
                _normalize_tag_number,
            ),
            seal_code_by_identity,
            clean_text=_clean_text,
            normalize_size=_normalize_size,
            normalize_gpn=_normalize_gpn,
            normalize_seal_name=_normalize_seal_name,
        )
    )
    return projection


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project the LTSA workbook into canonical pump/seal/inventory records."
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    projection = ingest_workbook(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(projection, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
