"""MWO-LTSA-CONTRACT-SCOPE-R3 -- read-only data access for ltsa_contract /
ltsa_contract_asset_scope (Chief Architect approved design, R2). No write
methods exist yet: R3 is explicitly a READ API foundation only -- contract
bootstrap/scoping is a separate, later, human-reviewed mission (R4).

Direct-Postgres, same convention as condition_monitoring_reading_repository.py/
pm_occurrence_repository.py (this exact domain's own established pattern) --
not a gateway/n8n workflow, since no such workflow exists for this new
domain either.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class LtsaContractRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_contracts(self) -> list[dict]:
        return _json_query(
            "SELECT contract_code, contract_name, customer_code, start_date, end_date, "
            "created_at, updated_at FROM ltsa_contract ORDER BY contract_code",
            self._runner,
        )

    def find_contract(self, contract_code: str) -> dict | None:
        rows = _json_query(
            "SELECT contract_code, contract_name, customer_code, start_date, end_date, "
            f"created_at, updated_at FROM ltsa_contract WHERE contract_code = {_sql(contract_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_scoped_assets_in_period(self, contract_code: str, period_start: str, period_end: str) -> list[dict]:
        """Every asset explicitly scoped to `contract_code` whose EFFECTIVE
        scope (per-asset override dates, falling back to the parent
        contract's own dates) overlaps [period_start, period_end] --
        exactly R2/R3's approved inclusive-interval-overlap rule. Never
        infers membership from asset_registry.status, ltsa_pumps, area,
        MA, or PM/CM history -- membership itself comes only from
        ltsa_contract_asset_scope existing, joined to asset_registry only
        for the identity/area fields this endpoint is allowed to expose.
        """
        return _json_query(
            "SELECT s.contract_code, s.asset_code, a.asset_type, a.area, "
            "s.scope_start_date, s.scope_end_date, "
            "COALESCE(s.scope_start_date, c.start_date) AS effective_scope_start, "
            "COALESCE(s.scope_end_date, c.end_date, 'infinity'::date) AS effective_scope_end "
            "FROM ltsa_contract_asset_scope s "
            "JOIN ltsa_contract c ON c.contract_code = s.contract_code "
            "JOIN asset_registry a ON a.asset_code = s.asset_code "
            f"WHERE s.contract_code = {_sql(contract_code)} "
            f"AND {_sql(period_start)}::date <= COALESCE(s.scope_end_date, c.end_date, 'infinity'::date) "
            f"AND {_sql(period_end)}::date >= COALESCE(s.scope_start_date, c.start_date) "
            "ORDER BY s.asset_code",
            self._runner,
        )

    def monitoring_summary_by_asset(self, asset_codes: list[str], period_start: str, period_end: str) -> dict[str, dict]:
        """Per-asset {reading_count_in_period, last_reading_date_in_period,
        last_reading_date_all_time} for exactly the given asset_codes.
        `last_reading_date_all_time` is deliberately NOT period-bound --
        it answers "when were we last actually here at all," a distinct,
        honest fact from "how many readings landed in this period" (the
        two together let a caller see e.g. an asset genuinely monitored
        before, just not within the selected window, rather than
        collapsing both into one ambiguous field). Excludes soft-deleted
        readings (deleted_at IS NOT NULL), same convention every other
        condition_monitoring_reading query in this codebase already
        follows.
        """
        if not asset_codes:
            return {}

        codes_sql = ", ".join(_sql(code) for code in asset_codes)
        rows = _json_query(
            "SELECT asset_code, "
            f"count(*) FILTER (WHERE reading_date BETWEEN {_sql(period_start)}::date AND {_sql(period_end)}::date) AS reading_count_in_period, "
            f"max(reading_date) FILTER (WHERE reading_date BETWEEN {_sql(period_start)}::date AND {_sql(period_end)}::date) AS last_reading_date_in_period, "
            "max(reading_date) AS last_reading_date_all_time "
            "FROM condition_monitoring_reading "
            f"WHERE asset_code IN ({codes_sql}) AND deleted_at IS NULL "
            "GROUP BY asset_code",
            self._runner,
        )
        return {row["asset_code"]: row for row in rows}


__all__ = ["LtsaContractRepository"]
