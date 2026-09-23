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


class AssetRegistryRepository:
    """Read-only canonical asset identity/type lookup."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def get_asset(self, asset_code: str) -> dict | None:
        rows = _json_query(
            "SELECT a.asset_code, a.asset_name, a.asset_type, a.area, "
            "a.asset_code AS tag_number, COALESCE(p.name, a.asset_name) AS name, "
            "NULL AS location, "
            "p.pump_type, p.status, p.seal_type, p.api_plan "
            "FROM public.asset_registry a LEFT JOIN public.ltsa_pumps p "
            "ON p.tag_number = a.asset_code "
            f"WHERE a.asset_code = {_sql(asset_code)} LIMIT 1",
            self._runner,
        )
        return rows[0] if rows else None

    def list_assets(self) -> list[dict]:
        return _json_query(
            "SELECT a.asset_code, a.asset_name, a.asset_type, a.area, "
            "a.asset_code AS tag_number, COALESCE(p.name, a.asset_name) AS name, "
            "NULL AS location, "
            "p.pump_type, p.status, p.seal_type, p.api_plan "
            "FROM public.asset_registry a LEFT JOIN public.ltsa_pumps p "
            "ON p.tag_number = a.asset_code WHERE a.asset_type = 'PUMP' "
            "AND NULLIF(BTRIM(a.asset_code), '') IS NOT NULL "
            "ORDER BY a.asset_code",
            self._runner,
        )
