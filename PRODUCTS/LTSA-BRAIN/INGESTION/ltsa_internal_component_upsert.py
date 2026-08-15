from __future__ import annotations

from typing import Any


def plan_internal_component_import(
    projection: dict[str, Any],
    state: dict[str, list[dict[str, Any]]],
    *,
    normalize_text: callable,
    is_blank: callable,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    projected_components = projection.get("internal_component_master", [])
    projected_stock = projection.get("internal_component_stock", [])
    projected_links = projection.get("seal_internal_component_link", [])
    existing_components = state.get("internal_components", [])
    existing_stock = state.get("internal_component_stock", [])
    existing_links = state.get("seal_internal_component_link", [])

    existing_by_id = {row["component_id"]: row for row in existing_components}
    existing_by_gpn = {normalize_text(row.get("gpn_number")): row for row in existing_components if normalize_text(row.get("gpn_number"))}
    existing_by_fingerprint = {normalize_text(row.get("identity_fingerprint")): row for row in existing_components if normalize_text(row.get("identity_fingerprint"))}
    existing_stock_by_id = {row["component_stock_id"]: row for row in existing_stock}
    existing_link_keys = {
        (row["seal_code"], row["component_id"], row["source_sheet_name"], row["source_row_number"]): row
        for row in existing_links
    }

    plan = {
        "internal_components": {"insert": [], "update": [], "unchanged": [], "rejected": []},
        "internal_component_stock": {"insert": [], "update": [], "unchanged": [], "rejected": []},
        "seal_internal_component_link": {"insert": [], "update": [], "unchanged": [], "rejected": []},
    }
    conflicts: list[dict[str, Any]] = []
    resolved_component_ids: dict[str, str] = {}

    for projected in projected_components:
        projected_id = projected["component_id"]
        projected_gpn = normalize_text(projected.get("gpn_number"))
        fingerprint = normalize_text(projected.get("identity_fingerprint"))
        existing_gpn = existing_by_gpn.get(projected_gpn) if projected_gpn else None
        existing_fp = existing_by_fingerprint.get(fingerprint) if fingerprint else None

        if existing_gpn is not None and existing_fp is not None and existing_gpn["component_id"] != existing_fp["component_id"]:
            conflicts.append(
                {
                    "classification": "conflict",
                    "component_id": projected_id,
                    "reason": "incoming GPN is already assigned to a different canonical component",
                    "gpn_number": projected_gpn,
                    "existing_component_id": existing_gpn["component_id"],
                    "fingerprint_component_id": existing_fp["component_id"],
                }
            )
            plan["internal_components"]["rejected"].append(projected_id)
            continue

        resolved_id = None
        if existing_gpn is not None:
            resolved_id = existing_gpn["component_id"]
        elif existing_fp is not None:
            resolved_id = existing_fp["component_id"]
        elif projected_id in existing_by_id:
            resolved_id = projected_id
        else:
            resolved_id = projected_id

        resolved_component_ids[projected_id] = resolved_id
        existing = existing_by_id.get(resolved_id)
        payload = {
            "component_id": resolved_id,
            "component_class": projected.get("component_class"),
            "gpn_number": projected_gpn,
            "gpn_status": projected.get("gpn_status"),
            "identity_fingerprint": fingerprint,
            "description": normalize_text(projected.get("description")),
            "size_text": normalize_text(projected.get("size_text")),
            "specification": normalize_text(projected.get("specification")),
            "source_workbook_name": normalize_text(projected.get("source_workbook_name")),
            "source_sheet_name": normalize_text(projected.get("source_sheet_name")),
            "source_row_number": projected.get("source_row_number"),
            "remarks": normalize_text(projected.get("remarks")),
        }

        if existing is None:
            plan["internal_components"]["insert"].append(payload)
            existing_by_id[resolved_id] = payload
            if projected_gpn:
                existing_by_gpn[projected_gpn] = payload
            if fingerprint:
                existing_by_fingerprint[fingerprint] = payload
            continue

        updates = {}
        for field in ("description", "size_text", "specification", "remarks", "source_workbook_name", "source_sheet_name"):
            if is_blank(existing.get(field)) and not is_blank(payload.get(field)):
                updates[field] = payload[field]
        if existing.get("source_row_number") is None and payload.get("source_row_number") is not None:
            updates["source_row_number"] = payload["source_row_number"]
        if is_blank(existing.get("identity_fingerprint")) and fingerprint:
            updates["identity_fingerprint"] = fingerprint
        if is_blank(existing.get("gpn_number")) and projected_gpn:
            updates["gpn_number"] = projected_gpn
            updates["gpn_status"] = "GPN_ASSIGNED"
        if updates:
            plan["internal_components"]["update"].append({"component_id": resolved_id, "fields": updates})
            existing.update(updates)
        else:
            plan["internal_components"]["unchanged"].append(resolved_id)

    rejected_ids = set(plan["internal_components"]["rejected"])
    for projected in projected_stock:
        source_component_id = projected["component_id"]
        if source_component_id in rejected_ids:
            plan["internal_component_stock"]["rejected"].append(projected["component_stock_id"])
            continue
        resolved_id = resolved_component_ids.get(source_component_id, source_component_id)
        payload = {
            "component_stock_id": projected["component_stock_id"],
            "component_id": resolved_id,
            "quantity_on_hand": projected.get("quantity_on_hand"),
            "warehouse_name": normalize_text(projected.get("warehouse_name")),
            "rack_name": normalize_text(projected.get("rack_name")),
            "location_tag": normalize_text(projected.get("location_tag")),
            "source_workbook_name": normalize_text(projected.get("source_workbook_name")),
            "source_sheet_name": normalize_text(projected.get("source_sheet_name")),
            "source_row_number": projected.get("source_row_number"),
            "remarks": normalize_text(projected.get("remarks")),
        }
        existing = existing_stock_by_id.get(projected["component_stock_id"])
        if existing is None:
            plan["internal_component_stock"]["insert"].append(payload)
            existing_stock_by_id[payload["component_stock_id"]] = payload
            continue
        updates = {}
        for field in ("component_id", "warehouse_name", "rack_name", "location_tag", "remarks"):
            if payload.get(field) != existing.get(field) and not is_blank(payload.get(field)):
                updates[field] = payload[field]
        if payload.get("quantity_on_hand") is not None and payload.get("quantity_on_hand") != existing.get("quantity_on_hand"):
            updates["quantity_on_hand"] = payload["quantity_on_hand"]
        if updates:
            plan["internal_component_stock"]["update"].append({"component_stock_id": payload["component_stock_id"], "fields": updates})
        else:
            plan["internal_component_stock"]["unchanged"].append(payload["component_stock_id"])

    for projected in projected_links:
        source_component_id = projected["component_id"]
        if source_component_id in rejected_ids:
            plan["seal_internal_component_link"]["rejected"].append(f"{projected['seal_code']}::{source_component_id}")
            continue
        resolved_id = resolved_component_ids.get(source_component_id, source_component_id)
        key = (projected["seal_code"], resolved_id, projected["source_sheet_name"], projected["source_row_number"])
        payload = {
            "seal_code": projected["seal_code"],
            "component_id": resolved_id,
            "relationship_basis": normalize_text(projected.get("relationship_basis")),
            "source_workbook_name": normalize_text(projected.get("source_workbook_name")),
            "source_sheet_name": normalize_text(projected.get("source_sheet_name")),
            "source_row_number": projected.get("source_row_number"),
        }
        existing = existing_link_keys.get(key)
        if existing is None:
            plan["seal_internal_component_link"]["insert"].append(payload)
        else:
            plan["seal_internal_component_link"]["unchanged"].append(f"{payload['seal_code']}::{payload['component_id']}::{payload['source_sheet_name']}::{payload['source_row_number']}")

    return plan, conflicts, resolved_component_ids
