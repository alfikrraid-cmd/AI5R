from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

_WORKBOOK_NAME = "04. LTSA Seal-JC TAP Stock Up To Date.xlsx"

_INTERNAL_COMPONENT_SHEETS = {
    "O-Ring": "O_RING",
    "Mating Ring": "MATING_RING",
    "Seal-Part": "SEAL_PART",
    "Mechanical Seal": "MECHANICAL_SEAL",
    "Mechanical Seal Assy": "MECHANICAL_SEAL_ASSY",
    "Shaft Sleeve": "SHAFT_SLEEVE",
    "Set Screw": "SET_SCREW",
    "Retiner": "RETAINER",
    "Sparepart": "SPARE_PART",
}

_GENERIC_COMPONENT_DESCRIPTIONS = {
    "MECHANICAL SEAL",
    "MECHANICAL SEAL ASSY",
    "MATING RING",
    "RETAINER ASM",
    "RETINER ASM",
    "SET SCREW",
    "SHAFT SLEEVE",
    "SEAL PART KIT",
}


def build_internal_component_id(
    component_class: str,
    *,
    gpn_number: str | None = None,
    identity_fingerprint: str | None = None,
) -> str:
    basis = f"GPN::{gpn_number}" if gpn_number else f"PENDING::{identity_fingerprint or component_class}"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16].upper()
    return f"LTSA-IC-{digest}"


def build_internal_component_stock_id(source_sheet_name: str, source_row_number: int) -> str:
    digest = hashlib.sha1(f"{source_sheet_name}::{source_row_number}".encode("utf-8")).hexdigest()[:16].upper()
    return f"LTSA-ICS-{digest}"


def project_internal_component_rows(
    sheet_rows: callable,
    clean_text: callable,
    normalize_size: callable,
    normalize_gpn: callable,
    parse_quantity: callable,
    normalize_seal_name: callable,
    normalize_tag_number: callable,
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    projected.extend(_project_o_ring_rows(sheet_rows("O-Ring"), clean_text, normalize_size, normalize_gpn, parse_quantity))
    projected.extend(
        _project_grouped_component_rows(
            sheet_rows("Mating Ring"),
            "Mating Ring",
            _INTERNAL_COMPONENT_SHEETS["Mating Ring"],
            {
                "start_row": 10,
                "description": 2,
                "size": 6,
                "tag_number": 7,
                "area": 8,
                "seal_type": 9,
                "pump_type": 10,
                "contract": 11,
                "quantity": 12,
                "warehouse": 13,
                "rack": 14,
                "location_tag": 15,
                "remarks": 16,
            },
            clean_text,
            normalize_size,
            parse_quantity,
            normalize_seal_name,
            normalize_tag_number,
        )
    )
    projected.extend(
        _project_grouped_component_rows(
            sheet_rows("Seal-Part"),
            "Seal-Part",
            _INTERNAL_COMPONENT_SHEETS["Seal-Part"],
            {
                "start_row": 10,
                "description": 2,
                "size": 6,
                "tag_number": 7,
                "area": 8,
                "seal_type": 9,
                "pump_type": 10,
                "contract": 11,
                "quantity": 12,
                "warehouse": 13,
                "rack": 14,
                "location_tag": 15,
                "remarks": 16,
            },
            clean_text,
            normalize_size,
            parse_quantity,
            normalize_seal_name,
            normalize_tag_number,
        )
    )
    for sheet_name in ("Mechanical Seal", "Mechanical Seal Assy", "Shaft Sleeve", "Retiner"):
        projected.extend(
            _project_grouped_component_rows(
                sheet_rows(sheet_name),
                sheet_name,
                _INTERNAL_COMPONENT_SHEETS[sheet_name],
                {
                    "start_row": 10,
                    "description": 2,
                    "size": 5,
                    "tag_number": 6,
                    "area": 7,
                    "seal_type": 8,
                    "pump_type": 9,
                    "contract": 10,
                    "quantity": 11,
                    "warehouse": 12,
                    "rack": 13,
                    "location_tag": 14,
                    "remarks": 15,
                },
                clean_text,
                normalize_size,
                parse_quantity,
                normalize_seal_name,
                normalize_tag_number,
            )
        )
    projected.extend(_project_set_screw_rows(sheet_rows("Set Screw"), clean_text, normalize_size, parse_quantity))
    projected.extend(_project_sparepart_rows(sheet_rows("Sparepart"), clean_text, normalize_size, parse_quantity, normalize_seal_name))
    return projected


def build_internal_component_projection(
    component_rows: list[dict[str, Any]],
    seal_code_by_identity: dict[tuple[str | None, str | None], str],
    *,
    clean_text: callable,
    normalize_size: callable,
    normalize_gpn: callable,
    normalize_seal_name: callable,
) -> dict[str, Any]:
    components: dict[str, dict[str, Any]] = {}
    stock_rows: dict[str, dict[str, Any]] = {}
    link_rows: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    rejected_rows: list[dict[str, Any]] = []

    for row in component_rows:
        gpn_number = normalize_gpn(row.get("gpn_number"))
        identity_fingerprint = _component_identity_fingerprint(row, clean_text, normalize_size)
        if gpn_number is None and not _supports_pending_component_identity(row, clean_text, normalize_size, normalize_seal_name):
            rejected_rows.append(
                {
                    "source_sheet_name": row["source_sheet_name"],
                    "source_row_number": row["source_row_number"],
                    "reason": "component identity is too generic to create a safe GPN_PENDING canonical component",
                }
            )
            continue

        component_id = build_internal_component_id(
            row["component_class"],
            gpn_number=gpn_number,
            identity_fingerprint=identity_fingerprint,
        )
        component = components.setdefault(
            component_id,
            {
                "component_id": component_id,
                "component_class": row["component_class"],
                "gpn_number": gpn_number,
                "gpn_status": "GPN_ASSIGNED" if gpn_number else "GPN_PENDING",
                "identity_fingerprint": identity_fingerprint or f"GPN::{gpn_number}",
                "description": clean_text(row.get("description")),
                "size_text": normalize_size(row.get("size_text")),
                "specification": clean_text(row.get("specification")),
                "source_workbook_name": _WORKBOOK_NAME,
                "source_sheet_name": row["source_sheet_name"],
                "source_row_number": row["source_row_number"],
                "remarks": clean_text(row.get("remarks")),
            },
        )
        if component["gpn_number"] is None and gpn_number is not None:
            component["gpn_number"] = gpn_number
            component["gpn_status"] = "GPN_ASSIGNED"

        stock_id = build_internal_component_stock_id(row["source_sheet_name"], row["source_row_number"])
        stock_rows[stock_id] = {
            "component_stock_id": stock_id,
            "component_id": component_id,
            "quantity_on_hand": row.get("quantity_on_hand"),
            "warehouse_name": clean_text(row.get("warehouse_name")),
            "rack_name": clean_text(row.get("rack_name")),
            "location_tag": clean_text(row.get("location_tag")),
            "source_workbook_name": _WORKBOOK_NAME,
            "source_sheet_name": row["source_sheet_name"],
            "source_row_number": row["source_row_number"],
            "remarks": clean_text(row.get("remarks")),
        }

        seal_identity = (
            normalize_seal_name(row.get("seal_type")),
            normalize_size(row.get("size_text")),
        )
        seal_code = seal_code_by_identity.get(seal_identity)
        if seal_code is not None:
            key = (seal_code, component_id, row["source_sheet_name"], row["source_row_number"])
            link_rows[key] = {
                "seal_code": seal_code,
                "component_id": component_id,
                "relationship_basis": "WORKBOOK_ROW",
                "source_workbook_name": _WORKBOOK_NAME,
                "source_sheet_name": row["source_sheet_name"],
                "source_row_number": row["source_row_number"],
            }

    backlog = Counter(component["component_class"] for component in components.values() if component["gpn_status"] == "GPN_PENDING")
    return {
        "internal_component_master": sorted(components.values(), key=lambda row: row["component_id"]),
        "internal_component_stock": sorted(stock_rows.values(), key=lambda row: row["component_stock_id"]),
        "seal_internal_component_link": sorted(link_rows.values(), key=lambda row: (row["seal_code"], row["component_id"], row["source_sheet_name"], row["source_row_number"])),
        "internal_component_rejections": rejected_rows,
        "internal_component_summary": {
            "component_count": len(components),
            "component_stock_count": len(stock_rows),
            "seal_link_count": len(link_rows),
            "rejected_row_count": len(rejected_rows),
            "gpn_assigned_count": sum(1 for component in components.values() if component["gpn_status"] == "GPN_ASSIGNED"),
            "gpn_pending_count": sum(1 for component in components.values() if component["gpn_status"] == "GPN_PENDING"),
            "gpn_pending_backlog": dict(sorted(backlog.items())),
        },
    }


def _project_o_ring_rows(rows, clean_text, normalize_size, normalize_gpn, parse_quantity):
    projected = []
    for row_number, columns in rows:
        if row_number < 11:
            continue
        row = {
            "source_sheet_name": "O-Ring",
            "source_row_number": row_number,
            "component_class": _INTERNAL_COMPONENT_SHEETS["O-Ring"],
            "description": clean_text(columns.get(2)),
            "size_text": normalize_size(columns.get(6)),
            "specification": None,
            "gpn_number": normalize_gpn(columns.get(7)),
            "quantity_on_hand": parse_quantity(columns.get(8)),
            "warehouse_name": clean_text(columns.get(9)),
            "rack_name": clean_text(columns.get(10)),
            "location_tag": clean_text(columns.get(11)),
            "remarks": clean_text(columns.get(12)),
            "seal_type": None,
        }
        if any(row[field] for field in ("description", "size_text", "gpn_number", "quantity_on_hand", "warehouse_name", "rack_name", "location_tag", "remarks")):
            projected.append(row)
    return projected

def _project_grouped_component_rows(
    rows,
    source_sheet_name,
    component_class,
    columns_map,
    clean_text,
    normalize_size,
    parse_quantity,
    normalize_seal_name,
    normalize_tag_number,
):
    state = {
        "description": None,
        "size": None,
        "tag_number": None,
        "area": None,
        "seal_type": None,
        "pump_type": None,
        "contract": None,
    }
    projected = []
    for row_number, columns in rows:
        if row_number < columns_map["start_row"]:
            continue
        for field in ("description", "size", "tag_number", "area", "seal_type", "pump_type", "contract"):
            index = columns_map.get(field)
            if index is None:
                continue
            if field == "size":
                value = normalize_size(columns.get(index))
            elif field == "seal_type":
                value = normalize_seal_name(columns.get(index))
            elif field == "tag_number":
                value = normalize_tag_number(columns.get(index))
            else:
                value = clean_text(columns.get(index))
            if value is not None:
                state[field] = value
        row = {
            "source_sheet_name": source_sheet_name,
            "source_row_number": row_number,
            "component_class": component_class,
            "description": state["description"],
            "size_text": state["size"],
            "specification": None,
            "gpn_number": None,
            "quantity_on_hand": parse_quantity(columns.get(columns_map["quantity"])),
            "warehouse_name": clean_text(columns.get(columns_map["warehouse"])),
            "rack_name": clean_text(columns.get(columns_map["rack"])),
            "location_tag": clean_text(columns.get(columns_map["location_tag"])),
            "remarks": clean_text(columns.get(columns_map["remarks"])),
            "seal_type": state["seal_type"],
            "pump_type": state["pump_type"],
            "tag_number": state["tag_number"],
            "contract": state["contract"],
        }
        if any(row[field] for field in ("description", "size_text", "quantity_on_hand", "warehouse_name", "rack_name", "location_tag", "remarks", "seal_type")):
            projected.append(row)
    return projected


def _project_set_screw_rows(rows, clean_text, normalize_size, parse_quantity):
    projected = []
    for row_number, columns in rows:
        if row_number < 10:
            continue
        row = {
            "source_sheet_name": "Set Screw",
            "source_row_number": row_number,
            "component_class": _INTERNAL_COMPONENT_SHEETS["Set Screw"],
            "description": clean_text(columns.get(2)),
            "size_text": normalize_size(columns.get(5)),
            "specification": clean_text(columns.get(6)),
            "gpn_number": None,
            "quantity_on_hand": parse_quantity(columns.get(7)),
            "warehouse_name": clean_text(columns.get(8)),
            "rack_name": clean_text(columns.get(9)),
            "location_tag": None,
            "remarks": clean_text(columns.get(10)),
            "seal_type": None,
        }
        if any(row[field] for field in ("description", "size_text", "specification", "quantity_on_hand", "warehouse_name", "rack_name", "remarks")):
            projected.append(row)
    return projected


def _project_sparepart_rows(rows, clean_text, normalize_size, parse_quantity, normalize_seal_name):
    projected = []
    for row_number, columns in rows:
        if row_number < 5:
            continue
        specification = clean_text(columns.get(7))
        row = {
            "source_sheet_name": "Sparepart",
            "source_row_number": row_number,
            "component_class": _INTERNAL_COMPONENT_SHEETS["Sparepart"],
            "description": clean_text(columns.get(2)),
            "size_text": normalize_size(columns.get(6)),
            "specification": specification,
            "gpn_number": None,
            "quantity_on_hand": parse_quantity(columns.get(8)),
            "warehouse_name": clean_text(columns.get(9)),
            "rack_name": clean_text(columns.get(10)),
            "location_tag": None,
            "remarks": clean_text(columns.get(11)),
            "seal_type": normalize_seal_name(specification),
        }
        if any(row[field] for field in ("description", "size_text", "specification", "quantity_on_hand", "warehouse_name", "rack_name", "remarks")):
            projected.append(row)
    return projected


def _component_identity_fingerprint(row, clean_text, normalize_size):
    description = clean_text(row.get("description"))
    size_text = normalize_size(row.get("size_text"))
    specification = clean_text(row.get("specification"))
    component_class = clean_text(row.get("component_class"))
    if component_class is None or description is None:
        return None
    return "|".join([component_class, description, size_text or "", specification or ""])


def _supports_pending_component_identity(row, clean_text, normalize_size, normalize_seal_name):
    description = (clean_text(row.get("description")) or "").upper()
    size_text = normalize_size(row.get("size_text"))
    specification = clean_text(row.get("specification"))
    seal_type = normalize_seal_name(row.get("seal_type"))
    if description and description not in _GENERIC_COMPONENT_DESCRIPTIONS:
        return True
    return any([size_text, specification, seal_type])
