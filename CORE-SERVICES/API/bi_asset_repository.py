"""LTSA_POWER_BI_R1B -- DIM_ASSET source for the governed BI read layer.

asset_registry is the authoritative asset population; ltsa_pumps is
enrichment only (LEFT JOIN on tag_number = asset_code), so an asset -- a
PUMP included -- is never dropped because it has no ltsa_pumps row.
Blank enrichment text is returned as NULL, never as "Unknown". One bulk
query; read-only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class BiAssetRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_assets_with_pump_enrichment(self) -> list[dict[str, Any]]:
        return _json_query(
            "SELECT ar.asset_code, ar.asset_name, ar.asset_type, ar.status AS asset_status, "
            "ar.area AS raw_area, (lp.tag_number IS NOT NULL) AS pump_enrichment_present, "
            "NULLIF(btrim(lp.pump_type), '') AS pump_type, NULLIF(btrim(lp.api_plan), '') AS api_plan, "
            "NULLIF(btrim(lp.seal_type), '') AS configured_seal_type, "
            "NULLIF(btrim(lp.criticality), '') AS criticality, NULLIF(btrim(lp.location), '') AS ltsa_location "
            "FROM asset_registry ar LEFT JOIN ltsa_pumps lp ON lp.tag_number = ar.asset_code "
            "ORDER BY ar.asset_code",
            self._runner,
        )


__all__ = ["BiAssetRepository"]
