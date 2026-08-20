"""Retire active seal-pump compatibility into immutable legacy evidence."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class SealPumpCompatibilityRetirementError(ValueError):
    pass


class SealPumpCompatibilityRetirementService:
    """Archive active compatibility evidence before deleting the active row.

    The legacy table intentionally keeps original_pump_tag_number as plain
    evidence, not as a FK to ltsa_pumps, because retired 946 tags are not
    canonical pumps.
    """

    _HISTORY_COLUMNS = (
        "compatibility_history_id, seal_code, original_pump_tag_number, "
        "original_compatibility_key, original_notes, original_created_at, "
        "source_reference, retirement_reason, retired_by, retired_at"
    )

    def __init__(self, runner: "DatabaseRunner"):
        self._runner = runner

    def retire(
        self,
        *,
        seal_code: str,
        pump_tag_number: str,
        retirement_reason: str,
        retired_by: str | None = None,
        source_reference: str | None = None,
    ) -> dict[str, Any] | None:
        seal_code = self._required("seal_code", seal_code)
        pump_tag_number = self._required("pump_tag_number", pump_tag_number)
        retirement_reason = self._required("retirement_reason", retirement_reason)

        self._runner.execute_script(
            f"""
            BEGIN;
            WITH active AS (
                SELECT seal_code, pump_tag_number, notes, created_at
                FROM public.seal_pump_compatibility
                WHERE seal_code = {_sql(seal_code)}
                  AND pump_tag_number = {_sql(pump_tag_number)}
                FOR UPDATE
            ),
            inserted AS (
                INSERT INTO public.seal_pump_compatibility_history (
                    seal_code,
                    original_pump_tag_number,
                    original_compatibility_key,
                    original_notes,
                    original_created_at,
                    source_reference,
                    retirement_reason,
                    retired_by
                )
                SELECT
                    seal_code,
                    pump_tag_number,
                    seal_code || '::' || pump_tag_number,
                    notes,
                    created_at,
                    {_sql(source_reference)},
                    {_sql(retirement_reason)},
                    {_sql(retired_by)}
                FROM active
                ON CONFLICT (seal_code, original_pump_tag_number) DO NOTHING
                RETURNING compatibility_history_id
            )
            DELETE FROM public.seal_pump_compatibility active_row
            WHERE active_row.seal_code = {_sql(seal_code)}
              AND active_row.pump_tag_number = {_sql(pump_tag_number)}
              AND (
                    EXISTS (SELECT 1 FROM inserted)
                 OR EXISTS (
                        SELECT 1
                        FROM public.seal_pump_compatibility_history history
                        WHERE history.seal_code = {_sql(seal_code)}
                          AND history.original_pump_tag_number = {_sql(pump_tag_number)}
                    )
              );
            COMMIT;
            """
        )

        rows = _json_query(
            f"""
            SELECT {self._HISTORY_COLUMNS}
            FROM public.seal_pump_compatibility_history
            WHERE seal_code = {_sql(seal_code)}
              AND original_pump_tag_number = {_sql(pump_tag_number)}
            """,
            self._runner,
        )
        return rows[0] if rows else None

    @staticmethod
    def _required(name: str, value: str | None) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise SealPumpCompatibilityRetirementError(f"{name} is required")
        return normalized
