from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


_INTERNAL_GPN_ROLES = frozenset({"SUPERUSER", "JOHN_CRANE_ENGINEER"})


def _list_response(rows: list[dict], total: int, limit: int, offset: int) -> dict:
    return {
        "success": True,
        "message": "Mechanical seal stock pools listed",
        "items": rows,
        "data": rows,
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
    }


class MechanicalSealStockRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_pools(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
        verification_status: str | None = None,
        include_gpn: bool = False,
    ) -> dict:
        filters = []
        if search:
            escaped = _sql(f"%{search.strip()}%")
            filters.append(
                "(p.seal_type ILIKE " + escaped
                + " OR p.nominal_size ILIKE " + escaped
                + " OR COALESCE(p.drawing_reference, '') ILIKE " + escaped
                + " OR EXISTS (SELECT 1 FROM public.mechanical_seal_stock_application sa_search "
                "WHERE sa_search.stock_pool_id = p.stock_pool_id AND sa_search.equipment_tag ILIKE "
                + escaped + "))"
            )
        if verification_status:
            filters.append(f"p.verification_status = {_sql(verification_status)}")
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        gpn = "p.complete_seal_gpn" if include_gpn else "NULL"
        rows = _json_query(
            "SELECT p.stock_pool_id, p.seal_code, p.seal_type, p.nominal_size, p.size_unit, "
            "p.application_size, p.physical_stock_size, p.drawing_reference, "
            f"{gpn} AS complete_seal_gpn, p.quantity_on_hand, p.quantity_reserved, "
            "p.quantity_available, p.stock_location, p.verification_status, p.compatibility_status, "
            "p.source_reference, p.notes, "
            "COALESCE((SELECT json_agg(sa ORDER BY sa.equipment_tag) FROM ("
            "SELECT stock_application_id, equipment_tag, seal_type_as_recorded, size_as_recorded, "
            "drawing_reference_as_recorded, "
            + ("complete_seal_gpn, " if include_gpn else "NULL AS complete_seal_gpn, ")
            + "configuration_marker, lifecycle_marker, area, "
            "equipment_type, contract_group, verification_status, compatibility_status, notes "
            "FROM public.mechanical_seal_stock_application sa WHERE sa.stock_pool_id = p.stock_pool_id"
            ") sa), '[]'::json) AS applications "
            "FROM public.mechanical_seal_stock_pool p "
            f"{where} ORDER BY p.seal_type, p.nominal_size, p.stock_pool_id "
            f"LIMIT {int(limit)} OFFSET {int(offset)}",
            self._runner,
        )
        total_rows = _json_query(
            "SELECT COUNT(*) AS total, SUM(p.quantity_on_hand) AS total_quantity "
            "FROM public.mechanical_seal_stock_pool p " + where,
            self._runner,
        )
        total = int(total_rows[0]["total"]) if total_rows else 0
        response = _list_response(rows, total, limit, offset)
        response["total_quantity"] = total_rows[0].get("total_quantity", 0) if total_rows else 0
        return response

    def get_pool(self, stock_pool_id: str, *, include_gpn: bool = False) -> dict | None:
        result = self.list_pools(limit=1, offset=0, search=stock_pool_id, include_gpn=include_gpn)
        rows = [row for row in result["items"] if row.get("stock_pool_id") == stock_pool_id]
        return rows[0] if rows else None

    def list_for_equipment(self, equipment_tag: str) -> list[dict]:
        return _json_query(
            "SELECT p.stock_pool_id, p.seal_code, p.seal_type, p.nominal_size, "
            "p.size_unit, p.application_size, p.physical_stock_size, "
            "p.drawing_reference, p.quantity_on_hand, p.quantity_reserved, "
            "p.quantity_available, p.stock_location, p.verification_status, "
            "p.compatibility_status, p.source_reference, p.notes, "
            "a.equipment_tag, a.complete_seal_gpn AS application_complete_seal_gpn, "
            "a.verification_status AS application_verification_status "
            "FROM public.mechanical_seal_stock_application a "
            "JOIN public.mechanical_seal_stock_pool p ON p.stock_pool_id = a.stock_pool_id "
            "WHERE a.equipment_tag = " + _sql(equipment_tag) + " "
            "ORDER BY p.seal_type, p.nominal_size, p.stock_pool_id",
            self._runner,
        )


def can_view_gpn(role: str | None) -> bool:
    return role in _INTERNAL_GPN_ROLES
